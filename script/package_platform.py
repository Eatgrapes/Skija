#! /usr/bin/env python3
import argparse, build_utils, common, os, sys, zipfile

def package():
  parser = argparse.ArgumentParser()
  parser.add_argument('--system', default=build_utils.system)
  parser.add_argument('--arch', default=build_utils.arch)
  (args, _) = parser.parse_known_args()

  os.chdir(common.basedir)
  classifier = f'{args.system}-{args.arch}'
  artifact = f'skija-{classifier}'

  platform_target = f'platform/target/{classifier}'

  build_utils.copy_replace(
    'platform/deploy/META-INF/maven/io.github.humbleui/pom.xml',
    f'{platform_target}/maven/META-INF/maven/io.github.humbleui/{artifact}/pom.xml',
    {'${version}': common.version, '${artifact}': artifact}
  )

  build_utils.copy_replace(
    'platform/deploy/META-INF/maven/io.github.humbleui/pom.properties',
    f'platform/target/{classifier}/maven/META-INF/maven/io.github.humbleui/{artifact}/pom.properties',
    {'${version}': common.version, '${artifact}': artifact}
  )

  with open(f'{platform_target}/classes/io/github/humbleui/skija/{args.system}/{args.arch}/skija.version', 'w') as f:
    f.write(common.version)

  build_utils.jar(f'target/{artifact}-{common.version}.jar',
                  (f'{platform_target}/classes', '.'),
                  (f'{platform_target}/maven', 'META-INF'))

  build_utils.jar(f'target/{artifact}-{common.version}-sources.jar',
                  (f'{platform_target}/maven', 'META-INF'))

  build_utils.jar(f'target/{artifact}-{common.version}-javadoc.jar',
                  (f'{platform_target}/maven', 'META-INF'))

  jmod_file = f'target/{artifact}-{common.version}.jmod'
  print(f"Packaging {os.path.basename(jmod_file)}")

  platform_package_dir = f'io/github/humbleui/skija/{args.system}/{args.arch}'
  lib_file = ''
  if args.system == 'macos':
    lib_file = 'libskija.dylib'
  elif args.system == 'linux' or args.system == 'android':
    lib_file = 'libskija.so'
  elif args.system == 'windows':
    lib_file = 'skija.dll'

  with open(jmod_file, mode='wb') as f:
    # Create empty jmod file with magic number
    f.write(b'JM\x01\x00PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

  with zipfile.ZipFile(jmod_file, 'a', compression=zipfile.ZIP_DEFLATED) as zf:
    zf.write(f'{platform_target}/classes/module-info.class', 'classes/module-info.class')
    zf.write(f'{platform_target}/classes/{platform_package_dir}/skija.version', f'classes/{platform_package_dir}/skija.version')
    zf.write(f'{platform_target}/classes/{platform_package_dir}/{lib_file}', f'lib/{lib_file}')
    if args.system == 'windows':
      zf.write(f'{platform_target}/classes/{platform_package_dir}/icudtl.dat', 'bin/icudtl.dat')

  return 0
