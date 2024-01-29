# Dieses Python-Skript enthält die Funktionen, welche zur Ermittlung der Benennung der Flugstreifen benötigt werden.
# Der Workflow wird durch Start von "main.py" initiiert, "flugstreifen_benennung.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024


from __future__ import annotations
import arcpy
import json
import os
import re
import csv
from info_wrapper import *


@func_info
def benennung_info_check(json_benennung_datei: str, workspace_info: list) -> list | bool:
    """
    Die Funktion überprüft, ob die Flugstreifen Benennung bereits einmal ermittelt wurde. Falls dies der Fall ist,
    wird diese direkt aus "name_flugstreifen.json" bezogen und nicht nochmals ermittelt.
    Parameter:
        - json_benennung_datei (str): Pfad zur json Datei, die die Flugstreifen-Benennung enthält
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - flugstreifen_info (list): Liste mit bereits ermittelter Flugstreifen Benennung, Subparts + Trennzeichen
          ODER
          False (bool): Flugstreifen Benennung muss erst ermittelt werden
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Check ob name_flugstreifen.json überhaupt existiert
    status = os.path.isfile(json_benennung_datei)
    if not status:
        # name.flugstreifen.json existiert noch nicht, wird erstellt
        f = open(json_benennung_datei, "x")
        f.close()
        return False

    with open(json_benennung_datei, "r") as file:
        # Load the JSON data from the file
        try:
            name_flugstreifen = json.load(file)
        except json.decoder.JSONDecodeError:
            # falls noch nichts in der json Datei steht
            return False

    for key, value in name_flugstreifen.items():
        if key == operat:
            flugstreifen_info = value
            return flugstreifen_info

    return False


@func_info
def benennung_struktur_erfassen(main_featureclasses_info: list) -> tuple:
    """
    Die Funktion ermittelt die Benennungsstruktur der Bildpunkte, damit erfasst werden kann, an welcher Stelle der
    Bildpunkt-Bezeichnung sich die relevante Flugstreifen-Nummer befindet.
    Parameter:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
    Rückgabewert:
        - bildpunkt_liste (list): Name und Shape der Bildpunkte als Liste
        - trennzeichen (str): Nicht-alphanumerisches Trennzeichen der Bildpunkt-Benennung
        - split_liste (list): List der getrennten Gruppen der Bildpunkt-Benennung
    """

    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    # Bildpunkte mit Benennung auslesen
    bildpunkt_liste = []
    with arcpy.da.SearchCursor(bildpunkte_unbearbeitet, ["img_name", "SHAPE@XY"]) as cursor:
        for row in cursor:
            bildpunkt_liste.append(row)

    # Ermittlung der Bildbezeichnungen und der Trennzeichen
    split_liste = []
    trennzeichen = []
    for img in bildpunkt_liste:
        # Aufsplitten bei nicht-alphanumerischen Zeichen ("Trennzeichen")
        img_split = re.split('[^a-zA-Z0-9]+', img[0])
        split_liste.append(img_split)

        # Trennzeichen finden (nicht-alphanumerische Zeichen)
        trennzeichen = re.findall('[^a-zA-Z0-9]+', img[0])

        trennzeichen = list(set(trennzeichen))
        if len(trennzeichen) != 1:
            raise Exception("Das Skript muss auf die neue Benennungsweise der Luftbilder angepasst werden!"
                            "\nunterschiedliche Trennzeichen gefunden!")

    trennzeichen = trennzeichen[0]
    return trennzeichen, split_liste, bildpunkt_liste


@func_info
def test_code_kompatibilitaet(split_liste: list):
    """
    Die Funktion prüft, ob die Benennung der einzelnen Bildpunkte einer Regelmäßigkeit unterliegen, d.h., ob anhand
    des Bildnamens die Flugstreifen Benennung ermittelt werden kann.
    Parameter:
        - split_liste (list): List der getrennten Gruppen der Bildpunkt-Benennung
    """

    img_subparts_len = len(split_liste[0])
    if img_subparts_len == 1:
        raise Exception("Das Skript muss auf die neue Benennungsweise der Luftbilder angepasst werden!"
                        "\nkeine non_alphanumerics als Trennzeichen gefunden!")

    for img in split_liste:
        if len(img) != img_subparts_len:
            raise Exception("Das Skript muss auf die neue Benennungsweise der Luftbilder angepasst werden!"
                            "\nFile Benennung in sich inkonsistent!")


@func_info
def match_subparts(split_liste: list, workspace_info: list) -> tuple:
    """
    Die Funktion ermittelt, wie oft sich ein Subpart in der Benennungsstruktur aller Bilder wiederholt. Es wird
    angenommen, dass wenige Matches bedeuten, dass es sich bei dem Subpart um den Bildnamen handelt.
    Parameter:
        - split_liste (list): List der getrennten Gruppen der Bildpunkt-Benennung
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - match_count_liste (list): Liste mit Anzahl der Wiederholungen einer Subpart-Bezeichnung
        - sample (list): Sample von Bildpunkten, unterteilt in Subparts
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    csv_file = rf"{operat_ordner}\flugstreifen_subpart_bestimmen.csv"

    # Sample von 25 Bildpunkten (Abstand von 20) erstellen, um Berechnungszeit zu minimieren
    sample = split_liste[:500:20]

    # Ermittlung, wie viele Teile (=subparts, getrennt durch nicht alpha-numerische Zeichen) die Bildpunkt-Benennung hat
    sample_subparts = len(sample[0])
    header = [str(x) for x in range(sample_subparts)]

    match_count_liste = []
    with open(csv_file, 'w', newline='') as csvfile:
        writer_fl = csv.writer(csvfile, delimiter=';')
        writer_fl.writerow(header)

        # Jeder subpart einer Bildpunkt-Benennung wird mit jeden korrespondierenden subparts aller anderen Bildpunkte
        # verglichen. Ist der Subpart gleich, so wird an match_count um 1 erhöht.
        # Die Matches werden in der Liste list_match_count gespeichert und in ein csv_file geschrieben.

        for subpart_count in range(sample_subparts):
            match_count = 0
            for bild in sample:
                for match_bild in range(len(sample)):
                    if bild[subpart_count] == sample[match_bild][subpart_count]:
                        match_count += 1
            match_count_liste.append(match_count)
        writer_fl.writerow(match_count_liste)
    print(match_count_liste)
    return match_count_liste, sample


@func_info
def flugstreifen_ermitteln(match_count_liste: list, sample: list, trennzeichen: str, bildpunkt_liste: list,
                           workspace_info: list) -> list:
    """
    Diese Funktion ermittelt die Flugstreifen, anhand der Flugstreifen Benennung. In "punkte_auf_linie" wird dies
    dann überprüft.
    Parameter:
        - match_count_liste (list): Liste mit Anzahl der Wiederholungen einer Subpart-Bezeichnung
        - sample (list): Sample von Bildpunkten, unterteilt in Subparts
        - trennzeichen (str): Nicht-alphanumerisches Trennzeichen der Bildpunkt-Benennung
        - bildpunkt_liste (list): Name und Shape der Bildpunkte als Liste
    Rückgabewert:
        - flugstreifen_info (list): Liste mit bereits ermittelter Flugstreifen Benennung, Subparts + Trennzeichen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Der Subpart von "flugstreifen_info" mit den wenigsten Matches wird entfernt (es wird angenommen, dass sich hier
    # die Bildnummer befindet)
    enum = enumerate(match_count_liste)
    flugstreifen_info = dict((i, j) for i, j in enum)
    kleinster_match_wert = min(flugstreifen_info, key=flugstreifen_info.get)
    del flugstreifen_info[kleinster_match_wert]

    # der Index des Subparts mit den wenigsten Matches wird an "ungunst_liste" angefügt
    ungunst_liste = [kleinster_match_wert]

    # Falls das flugstreifen_info nun eine Länge von 1 hat, wird angenommen, dass es sich beim Verbleibenden Subpart um
    # die Flugstreifen Benennung handelt.
    if len(flugstreifen_info) == 1:
        return [flugstreifen_info, trennzeichen]

    # Falls noch mehrere Subparts existieren wird nun iterativ überprüft, ob Punkte mit gleicher Benennung auf einer
    # Linie liegen (= Flugstreifen)
    else:
        while True:
            # Flugstreifen-Benennung anhand von "ungunst_liste" kürzen
            temp_flugstreifen_bezeichnung = benennung_kuerzen(
                sample,
                ungunst_liste,
                trennzeichen
            )

            # Flugstreifen-Name zur Geometrie hinzufügen
            temp_flugstreifen_bez_geo = geometrie_hinzufuegen(
                temp_flugstreifen_bezeichnung,
                bildpunkt_liste
            )

            # Test, ob sich die ermittelten Bildpunkte auf einer Linie befinden
            benennung_ermittelt = punkte_auf_linie_test(
                temp_flugstreifen_bez_geo,
                workspace_info
            )

            if benennung_ermittelt:
                # Die Benennung wurde ermittelt
                return [flugstreifen_info, trennzeichen]

            elif not benennung_ermittelt:
                # Die Benennung wurde noch nicht ermittelt. Ein weiterer Subpart muss gelöscht werden und while-Schleife
                # nochmals ausgeführt werden.
                neuer_loesch_kandidat = min(flugstreifen_info, key=flugstreifen_info.get)
                del flugstreifen_info[neuer_loesch_kandidat]
                ungunst_liste.append(neuer_loesch_kandidat)
                continue


@func_info
def benennung_kuerzen(sample: list, ungunst_liste: list, trennzeichen: str) -> list:
    """
    Die Funktion kürzt die Flugstreifen-Benennung anhand des/r in der "ungunst_liste" vorgegebenen Index/Indizes.
    Es wird noch keine Geometrie verbunden.
    Parameter:
        - sample (list): Sample von Bildpunkten, unterteilt in Subparts
        - ungunst_liste (list): Index/Indizes des/r Subparts mit den wenigsten Matches
        - trennzeichen (str): Nicht-alphanumerisches Trennzeichen der Bildpunkt-Benennung
    Rückgabewert:
        - temp_flugstreifen_bezeichnung (list): Liste mit gekürzten Flugstreifen-Benennungen
    """

    # Kopie des Samples erstellen
    temp_sample = sample.copy()

    # Subparts löschen, die nicht die Flugstreifen-Bezeichnung enthalten (Index in ungunst_liste)
    for item in temp_sample:
        for index in sorted(ungunst_liste, reverse=True):
            del item[index]

    # subparts mit trennzeichen wieder zusammenfügen und in liste temp_flugstreifen_bezeichnung speichern
    temp_flugstreifen_bezeichnung = []
    for item in temp_sample:
        joined = trennzeichen.join(item)
        temp_flugstreifen_bezeichnung.append(joined)
    temp_flugstreifen_bezeichnung = list(set(temp_flugstreifen_bezeichnung))

    return temp_flugstreifen_bezeichnung


@func_info
def geometrie_hinzufuegen(temp_flugstreifen_bezeichnung: list, bildpunkt_liste: list) -> list:
    """
    Die Funktion fügt die passende das passende Element aus "temp_flugstreifen_bezeichnung" an die Bildpunktgeometrie an
    Parameter:
        - temp_flugstreifen_bezeichnung (list): Liste mit gekürzten Flugstreifen-Benennungen
        - bildpunkt_liste (list): Name und Shape der Bildpunkte als Liste
    Rückgabewert:
        - temp_flugstreifen_bez_geo (list): Liste mit gekürzter Flugstreifen-Benennung und Geometrie
    """

    temp_flugstreifen_bez_geo = []
    for bezeichnung in temp_flugstreifen_bezeichnung:
        for bildpunkt in bildpunkt_liste:
            if bezeichnung in bildpunkt[0]:
                # wenn Flugstreifen-Benennung sich im Bildnamen befindet
                temp = [bildpunkt[0], bildpunkt[1], bezeichnung]
                temp_flugstreifen_bez_geo.append(temp)
    return temp_flugstreifen_bez_geo


@func_info
def punkte_auf_linie_test(temp_flugstreifen_bez_geo: list, workspace_info: list) -> bool:
    """
    Die Funktion ermittelt, ob die Bildpunkte in einer Linie liegen. Dies geschieht durch das Dissolven der Punkte mit
    gleichem Wert bei "abgleich" (= flugstreifen-Bezeichnung). Anschließend wird die Minimum Bounding Geometry erstellt,
    die bei negativem Puffern um 50 Meter verschwindet, wenn die "temp_flugstreifen_bezeichnung" korrekt ist, ansonsten
    muss die Flugstreifen-Bezeichnung weiter ermittelt werden.
    Parameter:
        - temp_flugstreifen_bezeichnung (list): Liste mit gekürzten Flugstreifen-Benennungen
        - bildpunkt_liste (list): Name und Shape der Bildpunkte als Liste
    Rückgabewert:
        - status (bool): Flugstreifen-Bestimmung erfolgreich = True, Flugstreifen-Bestimmung fortfahren = False
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Featuredataset "flugstreifenbestimmung" erstellen und befüllen
    fc_flugstreifenbestimmung = arcpy.CreateFeatureclass_management(fds_temp, f"flugstreifenbestimmung_{operat}",
                                                                    "POINT")
    arcpy.AddFields_management(fc_flugstreifenbestimmung, [["img_name", "TEXT"], ["abgleich", "TEXT"]])
    with arcpy.da.InsertCursor(fc_flugstreifenbestimmung, ["img_name", "SHAPE@XY", "abgleich"]) as cursor:
        for item in temp_flugstreifen_bez_geo:
            cursor.insertRow(item)

    # Minimum Bounding Geometry von Bildpunkten mit gleichem Wert in "abgleich"erstellen
    bounding_geometry_fc = rf"{fds_temp}\bounding_geometry_{operat}"
    arcpy.MinimumBoundingGeometry_management(fc_flugstreifenbestimmung,
                                             bounding_geometry_fc,
                                             "CONVEX_HULL",
                                             "LIST",
                                             "abgleich")

    # Bounding Geometry negativ Buffern
    buffer_pfad = rf"{fds_temp}\bounding_buffer_{operat}"
    arcpy.Buffer_analysis(bounding_geometry_fc,
                          buffer_pfad,
                          "-50 Meters",
                          "FULL",
                          "ROUND",
                          "ALL",
                          None,
                          "PLANAR")

    # wenn durch das negative Puffern keine Flächen mehr vorhanden sind (count = 0), heißt dies, die Punkte lagen auf
    # einer Linie
    count = int(arcpy.arcpy.GetCount_management(buffer_pfad).getOutput(0))

    if count == 0:
        # keine Flächen mehr, Punkte lagen auf einer Linie, Flugstreifen Name ist somit ermittelt
        print("Flugstreifen Name wurde ermittelt")
        status = True
        return status

    else:
        # mindestens eine Fläche übrig, Punkte lagen auf einer Linie, wodurch die dadurch größere bounding geometry
        # nicht durch das negative Puffern eliminiert werden konnte. Flugstreifen Name muss weiter ermittelt werden.
        print("Flugstreifen wird weiter ermittelt...")
        status = False
        return status


@func_info
def benennung_info_schreiben(json_benennung_datei: str, flugstreifen_info: list, workspace_info: list) -> None:
    """
    Die Funktion speichert die Benennung des Flugstreifens in "json_benennung_datei", damit beim nächsten Aufruf
    die Benennung nicht nochmals ermittelt werden muss.
    Parameter:
        - json_benennung_datei (str): Pfad zur json Datei, die die Flugstreifen-Benennung enthält
        - flugstreifen_info (list): Liste mit bereits ermittelter Flugstreifen Benennung, Subparts + Trennzeichen
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    status = os.path.isfile(json_benennung_datei)

    # json Datei wird erstellt, falls diese noch nicht existiert
    if not status:
        file = open(json_benennung_datei, 'w')
        file.close()

    # bereits vorhandene Flugstreifen-Benennungen werden ausgelesen
    try:
        with open(json_benennung_datei, 'r') as json_file:
            benennung_data = json.load(json_file)
            print(benennung_data)
    except json.decoder.JSONDecodeError:
        benennung_data = {}

    # neue Flugstreifen-Benennung wird an die json-Datei angefügt
    benennung_data[operat] = flugstreifen_info
    print(flugstreifen_info)
    print(benennung_data)
    with open(json_benennung_datei, 'w') as json_file:
        json.dump(benennung_data, json_file, indent=2)
