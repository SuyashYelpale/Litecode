# build.spec
block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['C:\\path\\to\\your\\project'],
    binaries=[],
    datas=[('app\\static\\app.ico', 'static')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

exe = EXE(
    a,
    name='LiteCode',
    icon='app\\static\\app.ico',  # Path to your .ico file
    console=False,  # Set to True if you want console window
)