import 'package:flutter/material.dart';

import '../category_map.dart';
import '../services/api_client.dart';
import '../services/usage_service.dart';
import '../session.dart';

Color tierColor(String tier) {
  switch (tier) {
    case 'high':
      return Colors.red.shade700;
    case 'moderate':
      return Colors.orange.shade800;
    default:
      return Colors.green.shade700;
  }
}

class CheckinScreen extends StatefulWidget {
  const CheckinScreen({super.key, required this.session});

  final Session session;

  @override
  State<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends State<CheckinScreen> {
  final _usage = UsageService();
  final _mood = TextEditingController();

  Map<String, dynamic>? _config;
  UsageSnapshot? _snapshot;
  Map<String, dynamic>? _result;
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _mood.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final cfg = await widget.session.api.getConfig();
      final snap = await _usage.todayUsage();
      if (!mounted) return;
      setState(() {
        _config = cfg;
        _snapshot = snap;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not read screen time: $e';
        _loading = false;
      });
    }
  }

  String _today() {
    final n = DateTime.now();
    final m = n.month.toString().padLeft(2, '0');
    final d = n.day.toString().padLeft(2, '0');
    return '${n.year.toString().padLeft(4, '0')}-$m-$d';
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      // Re-read usage so the submitted numbers are current.
      final snap = await _usage.todayUsage();
      final res = await widget.session.api.checkin(
        day: _today(),
        hours: snap.hours,
        moodText: _mood.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _snapshot = snap;
        _result = res;
        _submitting = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _submitting = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not submit: $e';
        _submitting = false;
      });
    }
  }

  Widget _usageRow(String cat) {
    final cfg = _config!;
    final thresholds = cfg['thresholds_hours'] as Map<String, dynamic>;
    final limit = (thresholds[cat] as num).toDouble();
    final hours = _snapshot!.hours[cat] ?? 0.0;
    final over = hours > limit;
    final double ratio = limit <= 0 ? 0.0 : (hours / limit).clamp(0.0, 1.0).toDouble();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(kCategoryLabels[cat] ?? cat),
              Text(
                '${hours.toStringAsFixed(1)} h / ${limit.toStringAsFixed(1)} h',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: over ? Colors.red.shade700 : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: ratio,
            minHeight: 8,
            color: over ? Colors.red.shade600 : Colors.teal,
          ),
        ],
      ),
    );
  }

  Widget _resultCard(Map<String, dynamic> r) {
    final tier = r['tier'] as String;
    final recs = (r['recommendations'] as List<dynamic>);
    return Card(
      margin: const EdgeInsets.only(top: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Chip(
                  label: Text(tier.toUpperCase(), style: const TextStyle(color: Colors.white)),
                  backgroundColor: tierColor(tier),
                ),
                const SizedBox(width: 12),
                Text('Combined score ${(r['fused_score'] as num).toStringAsFixed(2)}'),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Text signal ${(r['text_risk'] as num).toStringAsFixed(2)} (${r['text_risk_source']}) · '
              'screen-time signal ${(r['behavior_score'] as num).toStringAsFixed(2)} (${r['behavior_source']})',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const Divider(height: 24),
            for (final rec in recs)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(rec['title'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 2),
                    Text(rec['body'] as String),
                  ],
                ),
              ),
            Text(r['disclaimer'] as String, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_config == null || _snapshot == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error ?? 'Something went wrong.', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Try again')),
            ],
          ),
        ),
      );
    }

    final snap = _snapshot!;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text("Today's screen time (read from your phone)",
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text('Total so far: ${snap.totalHours.toStringAsFixed(1)} h. Pull down to refresh.',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
          for (final cat in kCategories) _usageRow(cat),
          if (snap.topUnmapped.isNotEmpty)
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('Apps counted under "Other"', style: TextStyle(fontSize: 14)),
              children: [
                for (final e in snap.topUnmapped)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text(e.key),
                    trailing: Text('${e.value.toStringAsFixed(0)} min'),
                  ),
              ],
            ),
          const SizedBox(height: 16),
          Text('How did your day feel?', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _mood,
            minLines: 3,
            maxLines: 6,
            maxLength: 2000,
            decoration: const InputDecoration(
              hintText: 'Write a few sentences in your own words (at least 4 words).',
              border: OutlineInputBorder(),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: _submitting
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Submit check-in'),
          ),
          const SizedBox(height: 4),
          Text('You can submit again later today; the latest one is kept.',
              style: Theme.of(context).textTheme.bodySmall),
          if (_result != null) _resultCard(_result!),
        ],
      ),
    );
  }
}
