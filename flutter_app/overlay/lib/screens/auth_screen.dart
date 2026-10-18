import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../session.dart';

/// Replace [kConsentText] with the wording approved by your institution's ethics process.
const String kConsentText =
    'I agree to take part in this research study. The app will record the total time I spend in each '
    'category of apps each day (not which messages or pages I open), the short note I write about my day, '
    'and my answers to the questionnaires. This data is used for research and I can stop at any time. '
    'This app is a self-awareness aid, not a medical service.';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, required this.session, required this.onLoggedIn});

  final Session session;
  final VoidCallback onLoggedIn;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  late final TextEditingController _server =
      TextEditingController(text: widget.session.api.baseUrl);
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _register = false;
  bool _consent = false;
  bool _busy = false;
  String? _error;
  String? _age;
  String? _gender;
  String? _residence;

  static const _ages = ['18-24', '25-34', '35+', 'Prefer not to say'];
  static const _genders = ['Female', 'Male', 'Other', 'Prefer not to say'];
  static const _residences = ['Urban', 'Semi-urban', 'Rural'];

  @override
  void dispose() {
    _server.dispose();
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.session.setServer(_server.text);
      final api = widget.session.api;
      final String token;
      if (_register) {
        token = await api.register({
          'username': _user.text.trim(),
          'password': _pass.text,
          'consent': _consent,
          'age_group': _age,
          'gender': _gender,
          'residence': _residence,
        });
      } else {
        token = await api.login(_user.text.trim(), _pass.text);
      }
      await widget.session.saveToken(token);
      if (!mounted) return;
      widget.onLoggedIn();
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _dropdown(String label, String? value, List<String> items, ValueChanged<String?> onChanged) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: DropdownButtonFormField<String>(
        value: value,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        items: [for (final i in items) DropdownMenuItem(value: i, child: Text(i))],
        onChanged: onChanged,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_register ? 'Join the study' : 'Sign in')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextField(
              controller: _server,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: 'Server address',
                helperText: 'e.g. http://192.168.1.10:8000',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _user,
              autocorrect: false,
              decoration: const InputDecoration(labelText: 'Username', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pass,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Password',
                helperText: 'At least 8 characters',
                border: OutlineInputBorder(),
              ),
            ),
            if (_register) ...[
              _dropdown('Age group (optional)', _age, _ages, (v) => setState(() => _age = v)),
              _dropdown('Gender (optional)', _gender, _genders, (v) => setState(() => _gender = v)),
              _dropdown('Where do you live? (optional)', _residence, _residences,
                  (v) => setState(() => _residence = v)),
              const SizedBox(height: 12),
              CheckboxListTile(
                value: _consent,
                onChanged: (v) => setState(() => _consent = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
                title: const Text(kConsentText, style: TextStyle(fontSize: 13)),
              ),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy || (_register && !_consent) ? null : _submit,
              child: _busy
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_register ? 'Create account' : 'Sign in'),
            ),
            TextButton(
              onPressed: _busy ? null : () => setState(() => _register = !_register),
              child: Text(_register ? 'I already have an account' : 'Create an account'),
            ),
          ],
        ),
      ),
    );
  }
}
