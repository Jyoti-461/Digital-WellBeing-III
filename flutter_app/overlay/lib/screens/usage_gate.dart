import 'package:flutter/material.dart';

import '../services/usage_service.dart';

/// Shows [child] only once Usage Access has been granted; otherwise explains why it is needed.
/// Android does not show a normal permission pop-up for this: the student must switch it on in Settings.
class UsageGate extends StatefulWidget {
  const UsageGate({super.key, required this.child});

  final Widget child;

  @override
  State<UsageGate> createState() => _UsageGateState();
}

class _UsageGateState extends State<UsageGate> with WidgetsBindingObserver {
  final _usage = UsageService();
  bool? _granted;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _check();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _check();
  }

  Future<void> _check() async {
    bool ok;
    try {
      ok = await _usage.hasAccess();
    } catch (_) {
      ok = false;
    }
    if (mounted) setState(() => _granted = ok);
  }

  @override
  Widget build(BuildContext context) {
    final granted = _granted;
    if (granted == null) return const Center(child: CircularProgressIndicator());
    if (granted) return widget.child;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.phone_android, size: 56),
            const SizedBox(height: 16),
            Text('Allow Usage Access', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            const Text(
              'To fill in your screen time automatically, this app needs "Usage access". '
              'It only reads how long each app was open today, grouped into six categories, '
              'and never reads what you do inside other apps.\n\n'
              'Tap the button, find this app in the list, and switch it on. Then come back here.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            FilledButton(onPressed: _usage.openSettings, child: const Text('Open Settings')),
            TextButton(onPressed: _check, child: const Text("I've turned it on")),
          ],
        ),
      ),
    );
  }
}
