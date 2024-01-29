# Dieses Python-Skript führt die Suche nach der/n korrekten .prj-Datei(en) und das anschließende Kopieren ins
# Arbeitsverzeichnis, sowie die Extraktion der Bildinformation aus der .prj-Datei und die Bereinigung der
# Bildinformation durch.
# Der Workflow wird durch das Starten von "main.py" initiiert, "prj_funktionen.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024


from __future__ import annotations
import os
import shutil
from info_wrapper import *


@func_info
def prj_datei_suchen(datenquelle: str, workspace_info: list) -> list | bool:
    """
    Funktion sucht alle .prj-Dateien (Bildorientierungsdateien) am Pfad "datenquelle".
    Parameter:
        - datenquelle (str): Verzeichnis von .prj-Dateien und Luftbildern, angegeben in "main.py"
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - datenquelle_prj (list/bool): Liste aus Pfaden zu .prj-Datei(en) ODER False -> keine prj.Datei gefunden
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    alle_dateien = []
    # alle Dateipfade in "datenquelle"
    for root, dirs, files in os.walk(datenquelle):
        for file in files:
            file_path = os.path.join(root, file)
            alle_dateien.append(file_path)

    # alle Dateipfade vom Typ .prj
    alle_prj_dateien = [file for file in alle_dateien if file.endswith(".prj")]

    # alle .prj-Dateien des konkreten Operates
    gefundene_prj_dateien = [file for file in alle_prj_dateien if file.split("\\")[-1].startswith(operat)]

    if len(gefundene_prj_dateien) == 0:
        # keine .prj-Datei wurde gefunden
        return False
    else:
        # mindestens eine .prj-Datei wurde gefunden
        datenquelle_prj = gefundene_prj_dateien
        return datenquelle_prj


@func_info
def externe_prj_sammlung_durchsuchen(externe_prj_sammlung: str, workspace_info: list) -> str:
    """
    Funktion sucht .prj-Dateien (Bildorientierungsdateien) am Pfad "externe_prj_sammlung".
    Parameter:
        - externe_prj_sammlung (str): Verzeichnis von zusätzlichen, extra abgelagerten .prj-Dateien
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - datenquelle_prj (str): Pfaden zu .prj-Datei(en) in "externe_prj_sammlung"
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # "externe_prj_sammlung" wird an "speicherort" kopiert, falls nicht schon vorhanden
    directory_exists = os.path.exists(rf"{speicherort}\prj-files_2019-20")
    if not directory_exists:
        shutil.copytree(externe_prj_sammlung, rf"{speicherort}\prj-files_2019-20")

    datenquelle_prj = rf"{speicherort}\prj-files_2019-20\{operat}_tif.prj"
    file_exists = os.path.exists(datenquelle_prj)
    if file_exists:
        # die .prj-Datei des konkreten Operates existiert in "externe_prj_sammlung"
        return datenquelle_prj
    else:
        # die .prj-Datei des konkreten Operates existiert nicht
        raise Exception("Kein .prj file zu angegebenen Operat gefunden!\n"
                        "Eingaben überprüfen!")


@func_info
def prj_kopieren(datenquelle_prj: list, workspace_info: list) -> list:
    """
    Funktion erstellt jeweils 2 Kopien pro .prj-Datei (Bildorientierungsdatei) im "operat_ordner".
    Parameter:
        - datenquelle_prj (list): Liste aus Pfaden zu .prj-Datei(en)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - prj_kopie_pfade (list): Liste aus Pfaden zu Kopien der .prj-Datei(en) im "operat_ordner"
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Liste aus Pfaden zu Kopien der .prj-Datei(en) im "operat_ordner"
    prj_kopie_pfade = []

    for prj_file in datenquelle_prj:

        # 1. Kopie: Original
        prj_pfad_neu = shutil.copy(prj_file, operat_ordner)

        # 2. Kopie: zur Weiterverarbeitung mit Endung "_kopie.prj"
        prj_kopie_pfad = prj_pfad_neu.split(".prj")[0] + "_kopie.prj"
        shutil.copy(prj_file, prj_kopie_pfad)

        prj_kopie_pfade.append(prj_kopie_pfad)
    return prj_kopie_pfade


@func_info
def mehrere_suboperate_check(prj_kopie_pfade: list, workspace_info: list) -> str:
    """
    Funktion fügt prj.-Dateien, falls mehrere vorhanden sind, zusammen.
    Parameter:
        - prj_kopie_pfade (list): Liste aus Pfaden zu Kopien der .prj-Datei(en) im "operat_ordner"
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - prj_kopie (str): Pfad zu der .prj-Datei, aus der die Bild-Infos bezogen werden
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Normalfall: es existiert nur eine prj.-Datei
    if len(prj_kopie_pfade) == 1:
        prj_kopie = rf"{prj_kopie_pfade[0]}"

    # selten: mehrere .prj Dateien wurden gefunden. Die Dateien werden ausgelesen und zusammengeschrieben.
    else:
        combined_prj_files = ""
        for prj_file in prj_kopie_pfade:
            with open(prj_file, "r") as prj:
                data = prj.read()
                combined_prj_files += data

        prj_kopie = rf"{operat_ordner}\{operat}_combined.prj"
        with open(prj_kopie, "w") as writer:
            writer.write(combined_prj_files)
    return prj_kopie


@func_info
def bild_info_extrahieren(prj_kopie: str) -> list:
    """
    Die relevanten Zeilen werden von "prj_kopie" extrahiert.
    Parameter:
        - prj_kopie (str): Pfad zu der .prj-Datei, aus der die Bild-Infos bezogen werden.
    Rückgabewert:
        - bild_info_unbearbeitet (list): Liste mit noch nicht bereinigten Bildinformationen
    """
    bild_info_unbearbeitet = []

    # prj_kopie wird ausgelesen
    with open(prj_kopie, 'r') as f:
        old_data = f.read()
        old_data = old_data.split("\n")

        # Zeilen mit Foto-Nummer ("$PHOTO_NUM") und Orientierungsparametern ("$EXT_ORI") werden
        # "bild_info_unbearbeitet" angefügt
        count = 0
        for line in old_data:
            if "$PHOTO_NUM" in line:
                bild_info_unbearbeitet.append(line)
            elif "$EXT_ORI" in line:
                bild_info_unbearbeitet.append(old_data[count + 1])
            count += 1

    return bild_info_unbearbeitet


@func_info
def bild_info_editieren(bild_info_unbearbeitet: list) -> dict:
    """
    Funktion editiert "bild_info_unbearbeitet", dabei werden Bilder ohne Orientierungsparameter aussortiert, die
    strings bereinigt und die bild_info in einem dictionary gespeichert.
    Parameter:
            - bild_info_unbearbeitet (list): Liste mit noch nicht bereinigten Bildinformationen.
    Rückgabewert:
            - bild_info (dict): Dictionary mit key = Bildnummer und value = [Orientierungsparameter]
    """

    # Abschnitt 1: Bilder ohne Orientierungsinformation aussortieren
    img_info_empty_deleted = []
    skip_next = False
    for item in bild_info_unbearbeitet:
        if "$PHOTO_NUM" in item:
            if not skip_next:
                img_info_empty_deleted.append(item)
            skip_next = True
        else:
            img_info_empty_deleted.append(item)
            skip_next = False

    # Abschnitt 2: string-editing
    img_info_str_edited = []
    for item in img_info_empty_deleted:
        item = ' '.join(item.split())
        if "$PHOTO_NUM" in item:
            item = item.removeprefix("$PHOTO_NUM : ")
            img_info_str_edited.append(item)
        else:
            ext_ori_raw = item.split()
            ext_ori_edited = ext_ori_raw[1:4]
            img_info_str_edited.append(ext_ori_edited)

    # Abschnitt 3: Dictionary mit Bildinformation erstellen
    bild_info = {}
    for i in range(0, len(img_info_str_edited), 2):
        key = img_info_str_edited[i]
        value = img_info_str_edited[i + 1]
        bild_info[key] = value

    return bild_info


@func_info
def prj_umschreiben(hinzugefuegt_punkte_liste: list, workspace_info: list):
    """
    Die Funktion passt die Pfade jener Bilder, die hinzugefügt werden sollen auf die Benennung im Verzeichnis an.
    Parameter:
        - hinzugefuegt_punkte_liste (list): Liste mit allen Punkten, die in "punkte_sammlung" hinzugefügt wurden
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - prj_dateien (list): Liste mit Pfad(en) zu prj-Datei(en)
    """
    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Bildnamen anpassen
    hinzugefuegt_punkte_liste_korrigiert = [f"{item}_rgb.tif" for item in hinzugefuegt_punkte_liste]

    # prj.-Datei(en) ermitteln
    prj_kopie_unedited = [item for item in os.listdir(operat_ordner) if item.endswith("kopie.prj")]

    # Pfad zum .prj-Datei-Namen hinzufügen
    prj_dateien = [rf"{operat_ordner}\{item}" for item in prj_kopie_unedited]

    # .prj-Datei Pfade anpassen
    for item in prj_dateien:
        # Inhalt der prj. Datei auslesen
        with open(item, "r") as file:
            old_data = file.read()
            if rf"H:\LB1\TIFFJPEG_" in old_data:
                ist_stand = "1"
            elif rf"H:\LB2\TIFFJPEG_" in old_data:
                ist_stand = "2"
            else:
                raise Exception("Skript ist nicht an die Benennung im .prj-File angepasst")

        # Pfade korrigieren
        with open(item, "w") as file:
            # Datei leeren
            file.truncate()

            # Dictionary mit alter Pfad-Benennung als Key und neuer Pfad-Benennung als Value bei Bildern, die
            # hinzugefügt werden sollten
            pfadpaare = {}

            # Pfade anpassen
            for bild in hinzugefuegt_punkte_liste_korrigiert:
                alter_pfad_name = rf"H:\LB{ist_stand}\TIFFJPEG_{meridian}\{operat}\{bild}"
                neuer_pfad_name = alter_pfad_name.replace("H:", r"\\\\Rz0-fil-25\\bev_dlb$")
                pfadpaare[alter_pfad_name] = neuer_pfad_name

            # neue Pfade anstelle der alten Pfade in der .prj-Datei einfügen
            data = old_data
            for alt_pfad, neu_pfad in pfadpaare.items():
                data = data.replace(alt_pfad, neu_pfad)

            # .prj-Datei wieder befüllen
            file.write(data)

    return prj_dateien
