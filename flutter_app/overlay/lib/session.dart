import 'package:shared_preferences/shared_preferences.dart';

import 'services/api_client.dart';

/// Holds the API client plus the saved server address and login token.
class Session {
  Session._(this._prefs, this.api);

  final SharedPreferences _prefs;
  final ApiClient api;

  // 10.0.2.2 is the Android emulator's alias for the computer running the backend.
  // On a real phone, set this to your computer's LAN IP, e.g. http://192.168.1.10:8000
  // static const String defaultServer = 'http://10.0.2.2:8000';
  static const String defaultServer =
    'https://digital-wellbeing-api.onrender.com';

  static Future<Session> load() async {
    final prefs = await SharedPreferences.getInstance();
    final api = ApiClient(prefs.getString('server_url') ?? defaultServer, prefs.getString('token'));
    return Session._(prefs, api);
  }

  bool get loggedIn => api.token != null;

  Future<void> setServer(String url) async {
    api.baseUrl = url.trim();
    await _prefs.setString('server_url', api.baseUrl);
  }

  Future<void> saveToken(String token) async {
    api.token = token;
    await _prefs.setString('token', token);
  }

  Future<void> logout() async {
    api.token = null;
    await _prefs.remove('token');
  }
}
