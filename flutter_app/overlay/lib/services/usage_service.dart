import 'package:flutter/services.dart';

import '../category_map.dart';

class UsageSnapshot {
  UsageSnapshot({required this.hours, required this.topUnmapped});

  /// Hours per category key (always contains all six keys).
  final Map<String, double> hours;

  /// Heaviest apps that fell into 'other' because they are not in the category map: (package, minutes).
  final List<MapEntry<String, double>> topUnmapped;

  double get totalHours => hours.values.fold(0.0, (a, b) => a + b);
}

class UsageService {
  static const MethodChannel _channel = MethodChannel('edu.timscdr.wellbeing/usage');

  Future<bool> hasAccess() async {
    final ok = await _channel.invokeMethod<bool>('hasUsageAccess');
    return ok ?? false;
  }

  Future<void> openSettings() async {
    await _channel.invokeMethod<void>('openUsageAccessSettings');
  }

  Future<String> _ownPackage() async {
    final p = await _channel.invokeMethod<String>('packageName');
    return p ?? '';
  }

  /// Today's foreground time (since local midnight) grouped into the six categories.
  Future<UsageSnapshot> todayUsage() async {
    final own = await _ownPackage();
    final raw = await _channel.invokeMapMethod<String, double>('queryTodayUsage');
    final minutes = raw ?? <String, double>{};

    final perCategoryMinutes = <String, double>{for (final c in kCategories) c: 0.0};
    final unmapped = <String, double>{};

    minutes.forEach((pkg, mins) {
      if (isIgnored(pkg, own)) return;
      final cat = categoryFor(pkg);
      perCategoryMinutes[cat] = (perCategoryMinutes[cat] ?? 0.0) + mins;
      if (!kCategoryMap.containsKey(pkg)) {
        unmapped[pkg] = mins;
      }
    });

    final hours = <String, double>{
      for (final e in perCategoryMinutes.entries)
        e.key: double.parse((e.value / 60.0).toStringAsFixed(2)),
    };

    final top = unmapped.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    return UsageSnapshot(hours: hours, topUnmapped: top.take(8).toList());
  }
}
