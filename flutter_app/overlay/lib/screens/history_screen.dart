import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../session.dart';
import 'checkin_screen.dart' show tierColor;

String _todayString() {
  final n = DateTime.now();
  final m = n.month.toString().padLeft(2, '0');
  final d = n.day.toString().padLeft(2, '0');
  return '${n.year.toString().padLeft(4, '0')}-$m-$d';
}

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, required this.session});

  final Session session;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);

  List<dynamic> _checkins = [];
  List<dynamic> _assessments = [];
  Map<String, dynamic>? _insights;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = widget.session.api;
      final results = await Future.wait<dynamic>([
        api.history(days: 30),
        api.assessmentHistory(),
        api.insights(_todayString()),
      ]);
      if (!mounted) return;
      setState(() {
        _checkins = results[0] as List<dynamic>;
        _assessments = results[1] as List<dynamic>;
        _insights = results[2] as Map<String, dynamic>;
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
        _error = 'Could not load your history: $e';
        _loading = false;
      });
    }
  }

  // ------------------------------------------------------------------ shared widgets
  Widget _supportCard() {
    final support = _insights?['support'];
    if (support is! Map) return const SizedBox.shrink();
    final helplines = (support['helplines'] as List<dynamic>? ?? []);
    return Card(
      color: Colors.red.shade50,
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.favorite, color: Colors.red.shade700),
                const SizedBox(width: 8),
                const Text('Support', style: TextStyle(fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 8),
            Text(support['message'] as String),
            for (final h in helplines)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '${h['name']}: ${(h['numbers'] as List<dynamic>).join(' or ')}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _bulletRow(IconData icon, Color color, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }

  Widget _insightCard(String heading, String sectionKey) {
    final section = _insights?[sectionKey];
    if (section is! Map) return const SizedBox.shrink();
    final obs = (section['observations'] as List<dynamic>).cast<String>();
    final dos = (section['do'] as List<dynamic>).cast<String>();
    final donts = (section['dont'] as List<dynamic>).cast<String>();
    final disclaimer = (_insights?['disclaimer'] as String?) ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.insights),
                const SizedBox(width: 8),
                Text(heading, style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 12),
            for (final o in obs) _bulletRow(Icons.fiber_manual_record, Colors.teal, o),
            if (dos.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('What you can do',
                  style: TextStyle(fontWeight: FontWeight.w700, color: Colors.green.shade800)),
              const SizedBox(height: 6),
              for (final d in dos) _bulletRow(Icons.check_circle_outline, Colors.green.shade700, d),
            ],
            if (donts.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('What to try to avoid',
                  style: TextStyle(fontWeight: FontWeight.w700, color: Colors.orange.shade900)),
              const SizedBox(height: 6),
              for (final d in donts) _bulletRow(Icons.remove_circle_outline, Colors.orange.shade800, d),
            ],
            if (disclaimer.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(disclaimer, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }

  // ------------------------------------------------------------------ check-ins tab
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

  Widget _checkinsTab() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          _supportCard(),
          _insightCard('Insights from your check-ins', 'checkin'),
          if (_checkins.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: Text('No check-ins yet. They will appear here.')),
            )
          else ...[
            Text('Combined score, last 7 check-ins', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            _bars(_checkins),
            const Divider(height: 32),
            for (final e in _checkins)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: CircleAvatar(backgroundColor: tierColor(e['tier'] as String), radius: 8),
                title: Text(e['day'] as String),
                subtitle: Text(
                  'Screen time ${_totalHours(Map<String, dynamic>.from(e['hours'] as Map)).toStringAsFixed(1)} h · '
                  'text ${(e['text_risk'] as num).toStringAsFixed(2)} · '
                  'screen ${(e['behavior_score'] as num).toStringAsFixed(2)}',
                ),
                trailing: Text((e['fused_score'] as num).toStringAsFixed(2)),
              ),
          ],
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ questionnaires tab
  Widget _instrumentCard(String name, String title) {
    final items = _assessments.where((a) => a['instrument'] == name).toList();
    if (items.isEmpty) return const SizedBox.shrink();
    final latest = items.first;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'Latest: ${latest['total']} of ${latest['max_total']} · ${latest['band']} · '
              '${(latest['created_at'] as String).substring(0, 10)}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            if (items.length > 1) ...[
              const Divider(height: 20),
              for (final a in items.skip(1).take(6))
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text((a['created_at'] as String).substring(0, 10)),
                      Text('${a['total']} of ${a['max_total']} · ${a['band']}'),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _questionnairesTab() {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          _supportCard(),
          _insightCard('Insights from your questionnaires', 'questionnaire'),
          if (_assessments.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  'No questionnaires yet. Use the Questionnaires tab at the bottom to complete one.',
                  textAlign: TextAlign.center,
                ),
              ),
            )
          else ...[
            _instrumentCard('phq9', 'PHQ-9 (depression screening)'),
            _instrumentCard('gad7', 'GAD-7 (anxiety screening)'),
            _instrumentCard('pss10', 'PSS-10 (perceived stress)'),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Try again')),
            ],
          ),
        ),
      );
    }
    return Column(
      children: [
        TabBar(
          controller: _tabs,
          tabs: const [Tab(text: 'Check-ins'), Tab(text: 'Questionnaires')],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: [_checkinsTab(), _questionnairesTab()],
          ),
        ),
      ],
    );
  }
}
