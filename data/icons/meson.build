application_id = APPLICATION_ID

scalable_dir = join_paths('hicolor', 'scalable', 'apps')
# Copy and rename existing icon to match new application_id
configure_file(
  input: join_paths(scalable_dir, 'io.github.Bavarder.Bavarder.svg'),
  output: ('@0@.svg').format(application_id),
  copy: true,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'icons', scalable_dir)
)

symbolic_dir = join_paths('hicolor', 'symbolic', 'apps')
configure_file(
  input: join_paths(symbolic_dir, 'io.github.Bavarder.Bavarder-symbolic.svg'),
  output: ('@0@-symbolic.svg').format(application_id),
  copy: true,
  install: true,
  install_dir: join_paths(get_option('datadir'), 'icons', symbolic_dir)
)
