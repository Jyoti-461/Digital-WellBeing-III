/// Package-name -> category lookup used on the device.
///
/// STARTER LIST. Package ids were written from general knowledge and can change or be wrong;
/// verify each one against the Play Store URL (the `id=` part) before the pilot. Anything not listed
/// is counted as 'other'. The check-in screen shows the heaviest unmapped apps so you can extend this
/// list with real data from your pilot devices.
const List<String> kCategories = [
  'social_media',
  'entertainment',
  'gaming',
  'productivity',
  'education',
  'other',
];

const Map<String, String> kCategoryLabels = {
  'social_media': 'Social Media',
  'entertainment': 'Entertainment',
  'gaming': 'Gaming',
  'productivity': 'Productivity',
  'education': 'Education',
  'other': 'Other',
};

const Map<String, String> kCategoryMap = {
  // Social media / messaging
  'com.instagram.android': 'social_media',
  'com.whatsapp': 'social_media',
  'com.facebook.katana': 'social_media',
  'com.facebook.orca': 'social_media',
  'com.snapchat.android': 'social_media',
  'com.twitter.android': 'social_media',
  'org.telegram.messenger': 'social_media',
  'com.linkedin.android': 'social_media',
  'com.reddit.frontpage': 'social_media',
  'com.pinterest': 'social_media',
  'com.discord': 'social_media',
  // Entertainment
  'com.google.android.youtube': 'entertainment',
  'com.google.android.apps.youtube.music': 'entertainment',
  'com.netflix.mediaclient': 'entertainment',
  'com.spotify.music': 'entertainment',
  'in.startv.hotstar': 'entertainment',
  'com.amazon.avod.thirdpartyclient': 'entertainment',
  'com.sonyliv': 'entertainment',
  'com.mxtech.videoplayer.ad': 'entertainment',
  // Gaming
  'com.tencent.ig': 'gaming',
  'com.pubg.imobile': 'gaming',
  'com.dts.freefireth': 'gaming',
  'com.dts.freefiremax': 'gaming',
  'com.activision.callofduty.shooter': 'gaming',
  'com.supercell.clashofclans': 'gaming',
  'com.supercell.clashroyale': 'gaming',
  'com.mojang.minecraftpe': 'gaming',
  'com.king.candycrushsaga': 'gaming',
  'com.roblox.client': 'gaming',
  // Productivity
  'com.google.android.gm': 'productivity',
  'com.google.android.apps.docs': 'productivity',
  'com.google.android.apps.docs.editors.docs': 'productivity',
  'com.google.android.apps.docs.editors.sheets': 'productivity',
  'com.google.android.apps.docs.editors.slides': 'productivity',
  'com.google.android.calendar': 'productivity',
  'com.google.android.keep': 'productivity',
  'com.google.android.apps.meetings': 'productivity',
  'com.microsoft.office.word': 'productivity',
  'com.microsoft.office.excel': 'productivity',
  'com.microsoft.office.powerpoint': 'productivity',
  'com.microsoft.office.outlook': 'productivity',
  'com.microsoft.teams': 'productivity',
  'us.zoom.videomeetings': 'productivity',
  'com.slack': 'productivity',
  // Education
  'com.duolingo': 'education',
  'org.khanacademy.android': 'education',
  'com.google.android.apps.classroom': 'education',
  'org.coursera.android': 'education',
  'com.udemy.android': 'education',
  'com.byjus.thelearningapp': 'education',
  'com.unacademyapp': 'education',
  'com.microblink.photomath': 'education',
};

/// System UI that should not count as the student's own screen use.
/// Heuristic substring match, so it may miss some manufacturers' launchers.
const List<String> kIgnoredSubstrings = ['launcher', 'systemui', 'inputmethod'];

String categoryFor(String pkg) => kCategoryMap[pkg] ?? 'other';

bool isIgnored(String pkg, String ownPackage) {
  if (pkg == ownPackage) return true;
  final lower = pkg.toLowerCase();
  for (final s in kIgnoredSubstrings) {
    if (lower.contains(s)) return true;
  }
  return false;
}
