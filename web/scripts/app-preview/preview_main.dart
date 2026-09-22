import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'main.dart' as original;
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({'access_token':'demo', 'refresh_token':'demo'});
  original.main();
}
