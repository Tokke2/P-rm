# Fil: folder_qt.py — kompatibelt startskript (v1.6.0)
# © Copyright Rickard Längkvist {get_copyright_year()} - All rights reserved
#
# Qt-versionen bor nu i folder.py (v1.6.0: tkinter ersatt av Qt).
# Detta skript finns kvar så att gamla genvägar och autostart-poster
# (som pekar på folder_qt.py) fortsätter fungera — det anropar bara
# folder.main().

from folder import main

if __name__ == "__main__":
    main()
