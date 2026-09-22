pass
from pathlib import Path
import shutil, subprocess, tempfile, os
root = Path(__file__).resolve().parents[2]
flutter = os.environ.get('FLUTTER_BIN') or shutil.which('flutter')
if not flutter:
    raise SystemExit('Set FLUTTER_BIN to your Flutter executable.')
with tempfile.TemporaryDirectory(prefix='study-app-preview-') as temp:
    work = Path(temp)
    for name in ('lib', 'web', 'pubspec.yaml', 'pubspec.lock'):
        source = root / 'frontend' / name
        if source.is_dir(): shutil.copytree(source, work / name)
        elif source.exists(): shutil.copy2(source, work / name)
    adapters = root / 'web/scripts/app-preview'
    for source in adapters.glob('*.dart'): shutil.copy2(source, work / 'lib' / source.name)
    shutil.copy2(adapters / 'api_client.dart', work / 'lib/services/api_client.dart')
    screen = work / 'lib/screens/chat_room_screen.dart'
    screen.write_text(screen.read_text().replace("import 'dart:io';", "import '../preview_socket.dart';"))
    subprocess.run([flutter, 'build', 'web', '--release', '--target=lib/preview_main.dart', '--base-href', '/app-version/', '--pwa-strategy', 'none', '--no-web-resources-cdn', '--no-wasm-dry-run'], cwd=work, check=True)
    target = root / 'web/public/app-version'
    shutil.copytree(work / 'build/web', target, dirs_exist_ok=True)
    print(f'App preview built at {target}')
