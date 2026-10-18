import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../session.dart';
import 'checkin_screen.dart' show tierColor;

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.session});

  final Session session;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic>? _entries;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final e = await widget.session.api.history(days: 30);
      if (!mounted) return;
      setState(() {
        _entries = e;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  double _totalHours(Map<String, dynamic> hours) =>
      hours.values.fold<double>(0.0, (a, b) => a + (b as num).toDouble());

  Widget _bars(List<dynamic> entries) {
    // Entries arrive newest-first; show the latest 7 oldest-to-newest.
    final recent = entries.take(7).toList().reversed.toList();
    return SizedBox(
      height: 130,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          for (final e in recent)
            Column(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text((e['fused_score'] as num).toStringAsFixed(2), style: const TextStyle(fontSize: 10)),
                const SizedBox(height: 2),
                Container(
                  width: 24,
                  height: 4 + 80 * (e['fused_score'] as num).toDouble().clamp(0.0, 1.0).toDouble(),
                  color: tierColor(e['tier'] as String),
                ),
                const SizedBox(height: 2),
                Text((e['day'] as String).substring(5), style: const TextStyle(fontSize: 10)),
              ],
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('Try again')),
          ],
        ),
      );
    }
    final entries = _entries ?? [];
    if (entries.isEmpty) {
      return const Center(child: Text('No check-ins yet. Your history will appear here.'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Combined score, last 7 check-ins', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          _bars(entries),
          const Divider(height: 32),
          for (final e in entries)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: tierColor(e['tier'] as String),
                radius: 8,
              ),
              title: Text(e['day'] as String),
              subtitle: Text(
                'Screen time ${_totalHours(Map<String, dynamic>.from(e['hours'] as Map)).toStringAsFixed(1)} h · '
                'text ${(e['text_risk'] as num).toStringAsFixed(2)} · '
                'screen ${(e['behavior_score'] as num).toStringAsFixed(2)}',
              ),
              trailing: Text((e['fused_score'] as num).toStringAsFixed(2)),
            ),
        ],
      ),
    );
  }
}
