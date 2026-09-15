# Candidates for further modules

A list of possible next LEAPP modules, checked against the current state of
`scripts/artifacts/` in all three repos the README names as a source
(iLEAPP/aLEAPP/rLEAPP), not just iLEAPP:

- [iLEAPP](https://github.com/abrignoni/iLEAPP) (iOS) — checked, see below.
- [aLEAPP](https://github.com/abrignoni/aLEAPP) (Android) — checked, see
  below.
- [RLEAPP](https://github.com/abrignoni/RLEAPP) — checked, but **no
  candidates from it**: "rLEAPP" stands for "Returns Logs Events And
  Properties Parser" and isn't a device-extraction parser like the other
  two — it parses **subpoena/legal-process "returns"**: records a provider
  (Google, Meta, Snap, Discord, …) hands over under court order, each in
  that provider's own export format. Practically the whole catalog there is
  provider-specific (`instagram*.py`, `fbig*.py`, `snap*.py`,
  `discordReturns*.py`, `googleReturnsmbox.py`, `takeout*.py`, …) — fits
  neither crush-analyze's "device image as input" model nor the "don't
  parse whole apps" boundary; if anything more provider-/app-specific than
  the iLEAPP/aLEAPP messenger parsers. Not a candidate for this mechanism.

File size is used only as a rough complexity proxy — nothing more.

**Important before implementing any of this:** the design doc
(`docs/design/analyzer-runner.md` in crush-forensics) is explicitly
cautious here — rollout step 8 says literally *"Decide on module 2 from
real use, not speculatively"*, and the non-goals explicitly rule out
*"systematic harvesting of LEAPP's whole module catalog"*. This list is
therefore a **pool to pick from when there's real need**, not a roadmap to
work through.

## Deliberately left out

Matching the goal ("don't parse whole apps"), excluded from this list:

- **Messenger/social/chat app parsers**, both iOS and Android:
  `whatsApp*.py`, `signalIOS.py`/`signalAndroid.py`, `signalLogs.py`,
  `telegramMesssages.py`, `telegramAccounts.py`/`telegramAndroid.py`,
  `discord_*.py`/`discordChats.py`/`discordApiCache.py`, `tikTok*.py`,
  `snapchat.py`, `instagramThreads.py`/`instagram.py`,
  `facebookMessenger.py`/`facebookApp.py`, `wickr.py`, `viber.py`/
  `Viber.py`, `line.py`, `wire.py`/`wireMessenger.py`, `slack.py`,
  `teams*.py`, `googleChat.py`, `groupMe.py`, `sessionIOS.py`/
  `sessionMessenger.py`, `ZaloChats.py`, `ZangiMessenger.py`, `meWe.py`/
  `mewe.py`, `mastodon.py`, `gettr.py`, `truthSocial.py`, `reddit.py`,
  `pinterest.py`, `grindr.py`, `tinder.py`, `bumble.py`, `weChat.py`,
  `kikMessenger.py`/`kik*.py`, `Threema.py`, `simplexChat.py`,
  `silentPhone.py`, `knuddels.py`, `truecaller.py`, `xiaohongshu.py`,
  `threads.py` — each a whole separate app with its own data model, exactly
  what the "where is this heading" concern rightly worries about.
- **Photos subsystem** (`Ph0*.py`, `photosMetadata.py`, `photosDbexif.py`,
  `googlePhotos.py`, …) — some files >100 KB, its own complex on its own,
  deliberately out of scope here.
- **Large cloud/finance/fitness/dating/streaming apps** (`googleDrive.py`,
  `googleMaps.py`, `spotify.py`/`Spotify.py`, `netflix.py`, `health.py`,
  `booking.py`, `garminConnect.py`/`garmin.py`, `Oura.py`,
  `WithingsHealthMate.py`, `fitbit.py`, `uber.py`, `ebay.py`, `etsy.py`,
  `disneyPlus.py`, `primeVideo.py`, `roblox.py`, `hinge.py`, `bereal.py`/
  `berealAndroid.py`, …) — same category: standalone app
  reverse-engineering projects, not small system artifacts.
- **`powerlog.py`, `knowledgeC.py`, `logarchive.py`, `chrome.py`,
  `keychain.py`** (iOS) and **`usagestats.py`, `appOpsModes.py`,
  `appOpsAccesses.py`, `permissionAccessState.py`, `chrome.py`,
  `netstats.py`** (Android) — high forensic value, but deliberately *not*
  in the candidate list below: all well over 25 KB, with noticeably more
  complex parsing logic than `applicationStateDB.py`. Not a reason to rule
  them out on principle, but a deliberate judgment call for "later, on
  real need," not as a starting point.
- **All of RLEAPP** — see reasoning above.

## iOS candidates (iLEAPP)

`applicationStateDB.py` (17,832 bytes, SQLite + plist blobs) as the
reference size.

### Directly complements the existing module

| File | Size | Why |
|---|---|---|
| `uninstalledApplications.py` | 2,810 B | Counterpart to `get_installed_apps` — same "Installed Apps" category, rounds out the existing module. |
| `mobileInstallb.py` | 5,964 B | App install/uninstall log, adds a timeline on top of `applicationState.db`'s pure state view. |

### Device/system metadata (small, few dependencies)

| File | Size | Why |
|---|---|---|
| `systemVersionPlist.py` | 5,965 B | Basic device info (iOS version, build), pure plist, barely any logic — a good second candidate to repeat the vendoring path on something simpler. |
| `simInfo.py` | 4,486 B | SIM/carrier info, often forensically relevant for device attribution. |
| `backupSettings.py` | 2,950 B | Backup configuration (iCloud vs. local, encrypted or not). |
| `deviceActivator.py` | 2,669 B | Activation metadata. |

### Connectivity/device history

| File | Size | Why |
|---|---|---|
| `bluetoothPairedLE.py` | 2,538 B | Paired BLE devices — clearly scoped SQLite source. |
| `bluetoothPairedReg.py` | 2,666 B | Same idea, classic Bluetooth. |
| `wifiIdentifiers.py` | 3,379 B | Known Wi-Fi networks. |
| `connectedDevices.py` | 3,165 B | USB/accessory connection history. |
| `iCloudWifi.py` | 3,245 B | iCloud-synced Wi-Fi list. |

### Higher forensic value, moderate complexity (next tier up from the above)

| File | Size | Why |
|---|---|---|
| `callHistory.py` | 7,233 B | Classic, highly requested artifact; SQLite-based, manageable. |
| `voicemail.py` | 8,107 B | Complements call history well. |
| `reminders.py` | 4,762 B | Simple SQLite structure, a good contrast to the plist-heavy modules. |
| `appleWalletCards.py` / `appleWalletTransactions.py` / `appleWalletPasses.py` | 3.4–5.9 KB each | Three small, thematically related wallet artifacts — a similar pattern to the three functions in `applicationStateDB.py`. |

## Android candidates (aLEAPP)

### Device/system metadata (small, few dependencies)

| File | Size | Why |
|---|---|---|
| `build.py` | 3,550 B | Android build/version props (`ro.build.*`) — Android analog to `systemVersionPlist.py`, pure key-value source. |
| `siminfo.py` | 4,033 B | SIM/carrier info — Android analog to `simInfo.py`. |
| `factory_reset.py` / `powerOffReset.py` / `oldpowerOffReset.py` / `shutdown_checkpoints.py` / `last_boot_time.py` | 2.1–2.3 KB each | Small, thematically related reboot/reset timeline. |

### Connectivity/device history

| File | Size | Why |
|---|---|---|
| `bluetoothConnections.py` | 4,506 B | Bluetooth connection history. |
| `wifiConfigstore2.py` | 4,485 B | Wi-Fi configuration. |
| `wifiProfiles.py` | 4,646 B | Known Wi-Fi profiles. |
| `wifiHotspot.py` | 3,529 B | Hotspot configuration/usage. |

### Installed apps (Android analog to the existing iOS module)

**Status: ported.** `installedappsVending.py` (Package Name, Title, First
Download, Last Updated, Install Reason, Auto-Update, Account) is vendored
as `get_installedappsVending` — `crush_analyze/vendored/leapp/android/
installedappsVending.py`, see [`porting-leapp-modules.md`](./porting-leapp-modules.md)
for the process. Two additions this port required in the compat shim:

- `does_column_exist_in_db`, new in `leapp_compat/ilapfuncs.py` (trivial,
  ~15-line PRAGMA query).
- `storagePathViews.py`'s `unique_files` helper, vendored (not
  reimplemented — see the reasoning in
  `vendored/leapp/android/MANIFEST.toml`) under
  `vendored/leapp/android/_helpers/`, registered as
  `scripts.artifacts.storagePathViews` alongside `scripts.ilapfuncs`.

Of the six candidates checked (`installedappsLibrary.py`,
`installedappsVending.py`, `installedappsGass.py`, `packageInfo.py`,
`packageRestrictions.py`, `packageUserStates.py`), `installedappsGass.py`
and `installedappsLibrary.py` were left unported (narrower data — version/
hash only, or purchase history only), as were the three ABX-based ones
(`packageInfo.py`, `packageRestrictions.py`, `packageUserStates.py` —
`ilapfuncs.abxread`/`checkabx`, a whole binary format, noticeably more
effort than a single trivial shim symbol).

### Higher forensic value, moderate complexity

| File | Size | Why |
|---|---|---|
| `calllogs.py` | 4,542 B | Classic call-log artifact. |
| `contacts.py` | 4,673 B | Contacts DB. |
| `telecomPhoneAccounts.py` | 6,974 B | Linked phone accounts (SIM/VoIP). |
| `downloads.py` | 3,855 B | Download history. |

## Proposed prioritization

1. **`systemVersionPlist.py` or `uninstalledApplications.py`** (iOS) as the
   next step, deliberately kept small — validates the process described in
   [`docs/porting-leapp-modules.md`](./porting-leapp-modules.md) a second
   time, on a module with as little surprise potential as possible (no
   further ilapfuncs-symbol or `Context` extension expected).
2. ~~Android sanity check~~ — done: `installedappsVending.py` is ported (see
   above), which doubled as the first proof that the `leapp_compat` shim
   works unmodified against an aLEAPP source, not just iLEAPP.
3. Only after that, **on real need** (design-doc principle), move toward
   `callHistory.py` / the wallet trio, or `calllogs.py`/`contacts.py`.
4. Deliberately hold off on the "click an app folder → open its parser"
   idea until it's clear whether that should be solved via curated modules
   (this mechanism) or via something fundamentally different — that would
   sit closer to the already-rejected "real plugin API" option from the
   design doc (non-goal: no dynamic loading of third-party code) than to
   "one more curated module".
