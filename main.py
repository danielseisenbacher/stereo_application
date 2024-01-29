# Dieses Python-Skript erfasst Benutzereingaben und koordiniert automatisch alle erforderlichen Abläufe.
# Es ist nicht nötig, andere Skripte separat zu starten; der Workflow wird durch das Starten von "main.py" initiiert.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024


from skript_koordination import input_parameter


# Pfad des Speicherorts sämtlicher Ergebnisse und Zwischenergebnisse.
speicherort = r"C:\Users\43664\OneDrive\Desktop\testdurchlauf\verzeichnis"


# Wird nur ein einzelnes Operat hinzugefügt, dann "mehrere_operate = False".
# Sollen mehrere Operate auf einmal hinzugefügt werden, dann "mehrere_operate = True".
mehrere_operate = False


# Falls "mehrere_operate = True" müssen hier die gewünschten Operate inklusive zugehöriger Meridianstreifen-Bezeichnung
# angeführt werden. Bei "mehrere_operate = False" kann "mehrere_operate_input" ignoriert werden.
# Form: "mehrere_operate_input = [["M28", "2020260"], ["M31", "2022450"], ["M34", "2021460"] ...]"
mehrere_operate_input = [["M31", "2022470"], ["M31", "2021260"], ["M31", "2023350"]]


# [["M28", "2020260"], ["M28", "2022370"], ["M28", "2019370"], ["M28", "2020550"],
# ["M28", "2020160"], ["M31", "2020460"], ["M31", "2022650"], ["M31", "2020150"],
# ["M31", "2021160"], ["M31", "2021250"], ["M31", "2021360"], ["M31", "2022160"],
# ["M31", "2020350"], ["M31", "2022350"], ["M31", "2022450"], ["M31", "2022260"],
# ["M31", "2022360"], ["M31", "2022460"], ["M34", "2021150"], ["M34", "2020250"],
# ["M34", "2021370"], ["M34", "2021450"], ["M34", "2021460"], ["M34", "2022150"],
# ["M34", "2022250"], ["M34", "2020360"], ["M34", "2021480"], ["M34", "2021350"],
# ["M31", "2022470"], ["M31", "2021260"], ["M31", "2023350"]]

# Soll ein Stereo Modell erstellt werden, "stereo_modell_erstellen = True".
# Andernfalls stereo_modell_erstellen = False
stereo_modell_erstellen = True


# Pfad des Verzeichnisses, in dem sich die Basisdaten, .prj-Dateien (Bildorientierungsdateien) und Luftbilder, befinden.
datenquelle = r"C:\Users\43664\OneDrive\Desktop\testdurchlauf\daten"


# Dateipfad zur Meridianstreifen-Featureclass.
meridianstreifen_pfad = r"C:\Users\43664\OneDrive\Desktop\Praktikum_Projekt\Operate\Operate\meridianstreifen.gdb\meridianstreifen_unbearbeitet"


# Dateipfad zum aktuellen digitalen Geländemodell.
dgm_pfad = r"\\RZ0-FIL-25\ALS$\ALS_BEV\Mosaik_2022_09_15\Lieferung\DGM\OeRect_01m_gt_31287.img"


# Bei Existenz eines Verzeichnisses mit zusätzlichen .prj-Dateien (Bildorientierungsdateien) ist der Verzeichnis-Pfad
# hier anzuführen.
externe_prj_sammlung = r"C:\Users\43664\OneDrive\Desktop\BA_Praxis\Operate\Operate\prj-files_2019-20"


input_parameter(speicherort, dgm_pfad, mehrere_operate, mehrere_operate_input, stereo_modell_erstellen,
                meridianstreifen_pfad, externe_prj_sammlung, datenquelle)
