import 'package:flutter/material.dart';

import '../session.dart';
import 'assessments_screen.dart';
import 'checkin_screen.dart';
import 'history_screen.dart';
import 'usage_gate.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.session, required this.onLoggedOut});

  final Session session;
  final VoidCallback onLoggedOut;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  int _historyTick = 0;

  Future<void> _logout() async {
    await widget.session.logout();
    widget.onLoggedOut();
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      UsageGate(child: CheckinScreen(session: widget.session)),
      HistoryScreen(key: ValueKey(_historyTick), session: widget.session),
      AssessmentsScreen(session: widget.session),
    ];
    const titles = ['Daily check-in', 'History', 'Questionnaires'];

    return Scaffold(
      appBar: AppBar(
        title: Text(titles[_index]),
        actions: [
          IconButton(tooltip: 'Sign out', icon: const Icon(Icons.logout), onPressed: _logout),
        ],
      ),
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() {
          _index = i;
          if (i == 1) _historyTick++; // reload history whenever its tab is opened
        }),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.edit_note), label: 'Check-in'),
          NavigationDestination(icon: Icon(Icons.show_chart), label: 'History'),
          NavigationDestination(icon: Icon(Icons.assignment), label: 'Questionnaires'),
        ],
      ),
    );
  }
}
