import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../session.dart';

class AssessmentsScreen extends StatefulWidget {
  const AssessmentsScreen({super.key, required this.session});

  final Session session;

  @override
  State<AssessmentsScreen> createState() => _AssessmentsScreenState();
}

class _AssessmentsScreenState extends State<AssessmentsScreen> {
  List<dynamic>? _list;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = await widget.session.api.listAssessments();
      if (!mounted) return;
      setState(() {
        _list = l;
        _error = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
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
    final list = _list;
    if (list == null) return const Center(child: CircularProgressIndicator());
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'These short questionnaires are used in the study to check how well the app\'s signals '
          'match established screening scales. Your researcher will tell you how often to complete them.',
        ),
        const SizedBox(height: 12),
        for (final i in list)
          Card(
            child: ListTile(
              title: Text(i['title'] as String),
              subtitle: Text('${i['n_items']} questions'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => AssessmentFormScreen(session: widget.session, name: i['name'] as String),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class AssessmentFormScreen extends StatefulWidget {
  const AssessmentFormScreen({super.key, required this.session, required this.name});

  final Session session;
  final String name;

  @override
  State<AssessmentFormScreen> createState() => _AssessmentFormScreenState();
}

class _AssessmentFormScreenState extends State<AssessmentFormScreen> {
  Map<String, dynamic>? _inst;
  List<int?> _answers = [];
  String? _error;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final inst = await widget.session.api.getAssessment(widget.name);
      if (!mounted) return;
      setState(() {
        _inst = inst;
        _answers = List<int?>.filled((inst['items'] as List<dynamic>).length, null);
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final res = await widget.session.api.submitAssessment(
        widget.name,
        _answers.map((a) => a!).toList(),
      );
      if (!mounted) return;
      setState(() => _submitting = false);
      await _showResult(res);
      if (!mounted) return;
      Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _submitting = false;
      });
    }
  }

  Future<void> _showResult(Map<String, dynamic> res) {
    final support = res['support'] as Map<String, dynamic>?;
    final helplines = support == null ? <dynamic>[] : (support['helplines'] as List<dynamic>);
    return showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Saved'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Score: ${res['total']} of ${res['max_total']} (${res['band']})'),
              const SizedBox(height: 8),
              Text(res['disclaimer'] as String, style: const TextStyle(fontSize: 12)),
              if (support != null) ...[
                const SizedBox(height: 16),
                Text(support['message'] as String),
                for (final h in helplines)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text('${h['name']}: ${(h['numbers'] as List<dynamic>).join(' or ')}',
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                  ),
              ],
            ],
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('OK'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final inst = _inst;
    return Scaffold(
      appBar: AppBar(title: Text(inst == null ? 'Questionnaire' : inst['title'] as String)),
      body: inst == null
          ? Center(child: _error == null ? const CircularProgressIndicator() : Text(_error!))
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(inst['prompt'] as String, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                for (var i = 0; i < _answers.length; i++) _question(inst, i),
                if (_error != null)
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: (_submitting || _answers.any((a) => a == null)) ? null : _submit,
                  child: _submitting
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Submit'),
                ),
              ],
            ),
    );
  }

  Widget _question(Map<String, dynamic> inst, int i) {
    final items = inst['items'] as List<dynamic>;
    final options = inst['options'] as List<dynamic>;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${i + 1}. ${items[i]}'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (var j = 0; j < options.length; j++)
                  ChoiceChip(
                    label: Text(options[j] as String),
                    selected: _answers[i] == j,
                    onSelected: (_) => setState(() => _answers[i] = j),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
