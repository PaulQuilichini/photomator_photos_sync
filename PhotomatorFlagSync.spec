# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('/usr/local/bin/exiftool', '.')],
    datas=[
        ('logo_poru_main.svg', '.'),
        ('/usr/local/bin/lib', 'lib'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotomatorFlagSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotomatorFlagSync',
)
app = BUNDLE(
    coll,
    name='PhotomatorFlagSync.app',
    icon=None,
    bundle_identifier='com.paulquilichini.photomatorflagsync',
    info_plist={
        'CFBundleName': 'PhotomatorFlagSync',
        'CFBundleDisplayName': 'PhotomatorFlagSync',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'NSPhotoLibraryUsageDescription': 'PhotomatorFlagSync scans your Photos library to avoid importing photos that are already there and to find duplicates.',
        'NSPhotoLibraryAddUsageDescription': 'PhotomatorFlagSync imports flagged photos into your Photos library and can add them to albums you choose.',
        'NSAppleEventsUsageDescription': 'PhotomatorFlagSync controls Photos to reveal duplicate matches in the app when you open them from DupeFind.',
    },
)
