#! /usr/bin/env python3
import argparse, build_utils, common, cross_compile, os, re, subprocess, sys, zipfile

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--debug', action='store_true')
  parser.add_argument('--arch', default=build_utils.arch)
  parser.add_argument('--system', default=build_utils.system)
  parser.add_argument('--skia-dir')
  parser.add_argument('--skia-release', default='m143-da51f0d60e')
  parser.add_argument('--cmake-toolchain-file')
  (args, _) = parser.parse_known_args()

  # Fetch Skia
  build_type = 'Debug' if args.debug else 'Release'
  if args.skia_dir:
    skia_dir = os.path.abspath(args.skia_dir)
    os.chdir(common.basedir + '/platform')
  else:
    os.chdir(common.basedir + '/platform')
    skia_dir = "Skia-" + args.skia_release + "-" + args.system + "-" + build_type + '-' + args.arch
    if not os.path.exists(skia_dir):
      zip = skia_dir + '.zip'
      build_utils.fetch('https://github.com/Eatgrapes/SkiaBuild/releases/download/' + args.skia_release + '/' + zip, zip)
      with zipfile.ZipFile(zip, 'r') as f:
        print("Extracting", zip, flush=True)
        f.extractall(skia_dir)
      os.remove(zip)
    skia_dir = os.path.abspath(skia_dir)
  print("Using Skia from", skia_dir, flush=True)

  # CMake
  classifier = f'{args.system}-{args.arch}'
  native_build_dir = f'target/{classifier}/native'
  build_utils.makedirs(native_build_dir)
  cmake_args = [
    'cmake',
    '-G', 'Ninja',
    '-DCMAKE_BUILD_TYPE=' + build_type,
    '-DSKIA_DIR=' + skia_dir,
    '-DSKIA_ARCH=' + args.arch]

  if args.system == 'macos':
    cmake_args += ['-DCMAKE_OSX_ARCHITECTURES=' + {'x64': 'x86_64', 'arm64': 'arm64'}[args.arch]]
  elif args.system == 'android':
    cmake_args += [
      '-DCMAKE_TOOLCHAIN_FILE=' + os.path.abspath(f'{common.basedir}/platform/cmake/android.toolchain.cmake'),
      '-DANDROID_NDK=' + os.environ.get('ANDROID_NDK_HOME'),
      '-DANDROID_ABI=' + {'arm64': 'arm64-v8a', 'x64': 'x86_64'}[args.arch],
      '-DANDROID_NATIVE_API_LEVEL=21' # Or higher, depending on requirements
    ]

  cmake_args += [os.path.abspath('.')]

  if args.cmake_toolchain_file:
    cmake_args += ['-DCMAKE_TOOLCHAIN_FILE=' + args.cmake_toolchain_file]
  elif (args.system == 'linux') and (args.arch != build_utils.native_arch):
    if args.arch == 'arm64':
      cross_compile.setup_linux_arm64(native_build_dir, cmake_args)

  subprocess.check_call(cmake_args, cwd=os.path.abspath(native_build_dir))

  # Ninja
  build_utils.ninja(os.path.abspath(native_build_dir))

  # Codesign
  if args.system == 'macos' and os.getenv('APPLE_CODESIGN_IDENTITY'):
    subprocess.call(['codesign',
                     # '--force',
                     # '-vvvvvv',
                     '--deep',
                     '--sign',
                     os.getenv('APPLE_CODESIGN_IDENTITY'),
                     f'{native_build_dir}/libskija.dylib'])
  # javac
  build_utils.javac(build_utils.files('../shared/java/**/*.java'),
                    '../shared/target/classes',
                    classpath = common.deps_compile(),
                    release = '8')
  build_utils.javac(build_utils.files('../shared/java9/**/*.java'),
                    '../shared/target/classes-java9',
                    classpath = common.deps_compile(),
                    modulepath = common.deps_compile(),
                    opts = ['--patch-module', 'io.github.humbleui.skija.shared=../shared/target/classes',],
                    release = '9')

  build_utils.copy_replace(
      'java/module-info.java',
      f'target/{classifier}/java/module-info.java',
      {'${system}': args.system, '${arch}': args.arch}
  )
  build_utils.javac(
      [f'target/{classifier}/java/module-info.java'],
      f'target/{classifier}/classes',
      release = '9',
      opts = ['-nowarn']
  )

  # Copy files
  target = f'target/{classifier}/classes/io/github/humbleui/skija/{args.system}/{args.arch}'

  if args.system == 'macos':
    build_utils.copy_newer(f'{native_build_dir}/libskija.dylib', f'{target}/libskija.dylib')
  elif args.system == 'linux':
    build_utils.copy_newer(f'{native_build_dir}/libskija.so', f'{target}/libskija.so')
  elif args.system == 'windows':
    build_utils.copy_newer(f'{native_build_dir}/skija.dll', f'{target}/skija.dll')
    build_utils.copy_newer(f'{skia_dir}/out/{build_type}-{args.arch}/icudtl.dat', f'{target}/icudtl.dat')
  elif args.system == 'android':
    build_utils.copy_newer(f'{native_build_dir}/libskija.so', f'{target}/libskija.so')

  return 0

if __name__ == '__main__':
  sys.exit(main())
