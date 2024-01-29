# Dieses Python-Skript koordiniert sämtliche lokalen Bearbeitungsschritte mit Vektordaten, das heißt ohne
# Berücksichtigung anderer Operate, unter anderem die Extraktion der Flugstreifen und die Ermittlung der
# relevanten Bildpunkte.
# Der Workflow wird durch das Starten von "main.py" initiiert, "vektor_lokal.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024

import arcpy
from info_wrapper import *


@func_info
def bildpunkte_einfuegen(bild_info: dict, main_featureclasses_info: list, workspace_info: list):
    """
    Die Bildpunkte werden in die Featureclass "bildpunkte_unbearbeitet" eingefügt.
    Parameter:
        - bild_info (dict): Dictionary mit key = Bildnummer und value = [Orientierungsparameter]
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """
    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    count = 0
    for i in bild_info.keys():
        count += 1
        img = i
        xy = (float(bild_info[i][0]), float(bild_info[i][1]))
        flugstreifen = "name nicht ermittelt"
        hoehe = bild_info[i][2]

        # Bildpunkte werden eingefügt mit Attributen: Bild-Name, Operatsnummer, Flugstreifen-Nummer, Flughöhe
        with arcpy.da.InsertCursor(bildpunkte_unbearbeitet,
                                   ["img_name", "operat", "flugstreifen", "flughoehe", "SHAPE@XY"]) as cursor:
            cursor.insertRow([img, operat, flugstreifen, hoehe, xy])


@func_info
def bildpunkte_inkl_flugstreifen_info(bild_info: dict, flugstreifen_info: list, main_featureclasses_info: list,
                                      workspace_info: list):
    """
    Die Bildpunkte werden in die Featureclasses "bildpunkte_extrahiert" und "bildpunkte_unbearbeitet" inklusive
    der nun vorhandenen Flugstreifen-Benennung durch "flugstreifen_info" eingefügt
    Parameter:
        - bild_info (dict): Dictionary mit key = Bildnummer und value = [Orientierungsparameter]
        - flugstreifen_info (list): Liste mit bereits ermittelter Flugstreifen Benennung, Subparts + Trennzeichen
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    subparts, trennzeichen = flugstreifen_info
    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    # Niedrigsten und höchsten relevanten Subpart-Index ermitteln (+1 bei max() wegen Slicing)
    name_indices = subparts.keys()
    name_indices = [int(x) for x in name_indices]
    max_index = max(name_indices) + 1
    min_index = min(name_indices)

    # "bildpunkte_extrahiert" mit Bildname, Operatsnummer, Flugstreifennummer, Flughöhe und Shape befüllen
    for bildname, orientierungsparamenter in bild_info.items():
        xy = (float(orientierungsparamenter[0]), float(orientierungsparamenter[1]))
        flugstreifen = bildname.split(trennzeichen)
        flugstreifen = flugstreifen[min_index:max_index]
        flugstreifen = trennzeichen.join(flugstreifen)
        hoehe = orientierungsparamenter[2]
        with arcpy.da.InsertCursor(bildpunkte_extrahiert,
                                   ["img_name", "operat", "flugstreifen", "flughoehe", "SHAPE@XY"]) as cursor:
            cursor.insertRow([bildname, operat, flugstreifen, hoehe, xy])

    # Features in "bildpunkte_unbearbeitet" kopieren
    arcpy.CopyFeatures_management(bildpunkte_extrahiert, bildpunkte_unbearbeitet)


@func_info
def flugstreifen_erstellen(main_featureclasses_info: list, workspace_info: list) -> str:
    """
    Die Funktion erstellt die Flugstreifen anhand des Feldes "flugstreifen" aus der Featureclass "bildpunkte_extrahiert"
    Parameter:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - flugstreifen_unbearbeitet (str): Pfad zur Featureclass mit allen unbearbeiteten Flugstreifen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    flugstreifen_unbearbeitet = rf"{fds_final}\flugstreifen_unbearbeitet"

    # Erstellen der Flugstreifen Featureclass, Verbinden der Punkte
    arcpy.PointsToLine_management(
        bildpunkte_extrahiert,
        flugstreifen_unbearbeitet,
        Line_Field="flugstreifen"
    )
    return flugstreifen_unbearbeitet


@func_info
def flugstreifen_ganz_ausserhalb(flugstreifen_unbearbeitet: str, oesterreich_buffer: str,
                                 main_featureclasses_info: list, workspace_info: list) -> str:
    """
    Die Funktion löscht sämtliche Flugstreifen, die außerhalb von Österreich liegen und die entsprechenden Bildpunkte
    in der Featureclass "bildpunkte_extrahiert".
    Parameter:
        - flugstreifen_unbearbeitet (str): Pfad zur Featureclass mit allen unbearbeiteten Flugstreifen
        - oesterreich_buffer (str): Pfad zur Featureclass mit gepuffert Fläche von Österreich
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - flugstreifen_ausserhalb (str): Pfad zur Featureclass mit allen Flugstreifen, die nicht in Ö liegen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    # Features auswählen, die sich außerhalb des gepufferten Staatsgebiets befinden
    flugstreifen_ausserhalb = rf"{fds_temp}\flugstreifen_ausserhalb_{operat}"
    streifen_ausserhalb, output_layer_names, count = arcpy.SelectLayerByLocation_management(
        in_layer=flugstreifen_unbearbeitet, overlap_type="INTERSECT", select_features=oesterreich_buffer,
        search_distance="", selection_type="NEW_SELECTION", invert_spatial_relationship="INVERT")
    # Features in Featureclass "flugstreifen_ausserhalb" kopieren
    arcpy.CopyFeatures_management(in_features=streifen_ausserhalb, out_feature_class=flugstreifen_ausserhalb,
                                  config_keyword="", spatial_grid_1=None, spatial_grid_2=None, spatial_grid_3=None)

    # Namen der Flugstreifen außerhalb von Ö speichern
    flugstreifen_ausserhalb_namen = []
    with arcpy.da.SearchCursor(flugstreifen_ausserhalb, ["flugstreifen"]) as cursor_1:
        for row in cursor_1:
            flugstreifen_ausserhalb_namen.append(row[0])

    # Flugstreifen außerhalb von Österreich löschen
    with arcpy.da.UpdateCursor(flugstreifen_unbearbeitet, ["flugstreifen"]) as cursor_2:
        for row in cursor_2:
            if row[0] in flugstreifen_ausserhalb_namen:
                cursor_2.deleteRow()

    # entsprechende Bildpunkte löschen
    with arcpy.da.UpdateCursor(bildpunkte_extrahiert, "flugstreifen") as cursor_3:
        for row in cursor_3:
            if row[0] in flugstreifen_ausserhalb_namen:
                cursor_3.deleteRow()

    return flugstreifen_ausserhalb


@func_info
def flugstreifen_richtung_berechnen(flugstreifen_unbearbeitet: str, workspace_info: list) -> tuple:
    """
    Die Funktion berechnet die Richtung der Flugstreifen und kopiert die Features in drei Featureclasses.
    Parameter:
        - flugstreifen_unbearbeitet (str): Pfad zur Featureclass mit allen unbearbeiteten Flugstreifen in Ö
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert (tuple):
        - flugstreifen_vertikal (str): Pfad zur Featureclass mit Flugstreifen in Nord-Süd-Ausdehnung
        - flugstreifen_horizontal (str): Pfad zur Featureclass mit Flugstreifen in Ost-West-Ausdehnung
        - flugstreifen_schraeg (str): Pfad zur Featureclass allen übrigen (schrägen) Ausdehnungen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    flugstreifen_schraeg = rf"{fds_temp}\flugstreifen_schraeg_{operat}"
    flugstreifen_vertikal = rf"{fds_temp}\flugstreifen_vertikal_{operat}"
    flugstreifen_horizontal = rf"{fds_temp}\flugstreifen_horizontal_{operat}"

    arcpy.DirectionalMean_stats(flugstreifen_unbearbeitet, flugstreifen_schraeg, Orientation_Only="DIRECTION",
                                Case_Field="flugstreifen")
    arcpy.CopyFeatures_management(flugstreifen_schraeg, flugstreifen_vertikal)
    arcpy.CopyFeatures_management(flugstreifen_schraeg, flugstreifen_horizontal)

    return flugstreifen_schraeg, flugstreifen_vertikal, flugstreifen_horizontal


@func_info
def schraege_flugstreifen(flugstreifen_schraeg: str) -> tuple:
    """
    Die Funktion ermittelt alle schrägen Flugstreifen und ermittelt, welche speichert die Namen jener, die gelöscht bzw.
    beibehalten werden sollen, in zwei Listen.
    Parameter:
        - flugstreifen_schraeg (str): Pfad zur Featureclass allen schrägen Ausdehnungen
    Rückgabewert (tuple):
        - schraege_flugstreifen_liste (list): Liste mit schrägen Flugstreifen (potenzielle Talstreifen)
        - ungunst_schraeg (list): Liste der schrägen Flugstreifen, die zu lange sind, um einen Flugstreifen darzustellen
    """

    ungunst_schraeg = []
    schraege_flugstreifen_liste = []
    with arcpy.da.UpdateCursor(flugstreifen_schraeg, ["CompassA", "flugstreifen", "Shape_Length"]) as cursor:
        for row in cursor:
            # alle Fluglinien aussortieren, die horizontal oder vertikal sind
            if row[0] >= 357 or row[0] <= 3:
                cursor.deleteRow()
            elif 177 <= row[0] <= 183:
                cursor.deleteRow()
            elif 87 <= row[0] <= 93:
                cursor.deleteRow()
            elif 267 <= row[0] <= 273:
                cursor.deleteRow()
            else:
                streifen_laenge = row[2]
                if streifen_laenge > 30000:
                    # lange schräge Flugstreifen sind mit Sicherheit nicht relevant
                    ungunst_schraeg.append(row[1])
                else:
                    # relevante Flugstreifen
                    schraege_flugstreifen_liste.append(row[1])

    return schraege_flugstreifen_liste, ungunst_schraeg


@func_info
def vertikale_flugstreifen(flugstreifen_vertikal: str):
    """
    Die Funktion ermittelt alle vertikalen Flugstreifen (Nord-Süd).
    Parameter:
        - flugstreifen_vertikal (str): Pfad zur Featureclass mit Flugstreifen in Nord-Süd-Ausdehnung
    """

    with arcpy.da.UpdateCursor(flugstreifen_vertikal, ["CompassA"]) as cursor:
        for field in cursor:
            # alle Fluglinien aussortieren, die nicht vertikal sind
            field = float(field[0])
            if field >= 357 or field <= 3:
                pass
            elif 177 <= field <= 183:
                pass
            else:
                cursor.deleteRow()


@func_info
def horizontale_flugstreifen(flugstreifen_horizontal: str):
    """
    Die Funktion ermittelt alle horizontalen Flugstreifen (Ost-West).
    Parameter:
        - flugstreifen_horizontal (str): Pfad zur Featureclass mit Flugstreifen in Ost-West-Ausdehnung
    """

    with arcpy.da.UpdateCursor(flugstreifen_horizontal, ["CompassA"]) as cursor:
        # alle Fluglinien aussortieren, die nicht horizontal sind
        for field in cursor:
            field = float(field[0])
            if 267 <= field <= 273:
                pass
            elif 87 <= field <= 93:
                pass
            else:
                cursor.deleteRow()


@func_info
def schraege_randstreifen_extrahieren(flugstreifen_schraeg: str, flugstreifen_ausserhalb: str, meridianstreifen: str,
                                      ungunst_schraeg: list, workspace_info: list) -> list:
    """
    Die Funktion ermittelt die schrägen Randstreifen des Operates und löscht dies, damit nur jene schrägen Flugstreifen
    verbleiben, bei denen Täler aufgenommen wurden. Die Liste ungunst_schraeg enthält alle Namen jener Flugstreifen,
    die gelöscht wurden.
    Parameter:
        - flugstreifen_schraeg (str): Pfad zur Featureclass allen schrägen Ausdehnungen
        - flugstreifen_ausserhalb (str): Pfad zur Featureclass mit allen Flugstreifen, die nicht in Ö liegen
        - merdianstreifen (str): Pfad zu Meridianstreifen Featureclass
        - ungunst_schraeg (list): Liste der schrägen Flugstreifen, die zu lange sind, um einen Flugstreifen darzustellen
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - flugstreifen_ungunst (list): Liste der Namen der schrägen Flugstreifen, die gelöscht werden
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Test, wie viel Prozent eines Flugstreifens außerhalb von Österreich liegt
    arcpy.CopyFeatures_management(flugstreifen_schraeg, flugstreifen_ausserhalb)
    arcpy.AddField_management(flugstreifen_ausserhalb, "laenge_gesamt", "DOUBLE")
    arcpy.CalculateField_management(flugstreifen_ausserhalb, "laenge_gesamt", "!Shape_Length!", "PYTHON3", '', "TEXT",
                                    "NO_ENFORCE_DOMAINS")

    # Clip mit Meridianfläche
    streifen_clip = rf"{fds_temp}\flugstreifen_clip_{operat}"
    arcpy.PairwiseClip_analysis(flugstreifen_ausserhalb, meridianstreifen, streifen_clip)

    # Falls weniger als 50 % der Gesamtlänge eines Flugstreifens innerhalb des Staatsgebietes liegt, wird
    # der Name in der Liste ungunst_streifen ausgegeben.
    flugstreifen_ungunst = []
    with arcpy.da.UpdateCursor(streifen_clip, ["laenge_gesamt", "Shape_Length", "flugstreifen"]) as cursor:
        for row in cursor:
            if row[1] < row[0] / 2:
                flugstreifen_ungunst.append(row[2])
            else:
                pass

    # Die Namen der Flugstreifen, die zu lang für Talstreifen waren, wird an "flugstreifen_ungunst" angefügt
    for item in ungunst_schraeg:
        flugstreifen_ungunst.append(item)

    # Die "flugstreifen_ungunst" werden gelöscht und die Namen returned
    with arcpy.da.UpdateCursor(flugstreifen_schraeg, ["Shape_Length"]) as cursor_2:
        for row in cursor_2:
            if row[0] in flugstreifen_ungunst:
                cursor_2.deleteRow()
            else:
                pass
    return flugstreifen_ungunst


@func_info
def schraege_randstreifen_bildpunkte_loeschen(main_featureclasses_info: list, flugstreifen_ungunst: list):
    """
    Die Funktion löscht Bildpunkte in "bildpunkte_extrahiert" anhand von flugstreifen_ungunst (schräge ungunst-streifen)
    Parameter:
        - flugstreifen_ungunst (list): Liste der Namen der schrägen Flugstreifen, die gelöscht werden
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
    """

    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info
    with arcpy.da.UpdateCursor(bildpunkte_extrahiert, "flugstreifen") as cursor:
        for row in cursor:
            # wenn Bildpunkt auf Flugstreifen liegt, der einen Wert von "flugstreifen_ungunst" hat, löschen
            if row[0] in flugstreifen_ungunst:
                cursor.deleteRow()


@func_info
def vertikale_streifen_bildpunkte_loeschen(main_featureclasses_info: list, flugstreifen_vertikal: str):
    """
    Alle Bildpunkte, die auf vertikalen Flugstreifen liegen werden gelöscht, da primär horizontal geflogen, wird
    und nur dann vertikale Bilder herangezogen werden sollen, wenn keine horizontalen verfügbar sind.
    Parameter:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - flugstreifen_vertikal (str): Pfad zur Featureclass mit Flugstreifen in Nord-Süd-Ausdehnung
    """

    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    # Die Namen der vertikalen Streifen werden in die Liste vertikale_stabilisatoren gespeichert
    vertikale_stabilisatoren = []
    with arcpy.da.SearchCursor(flugstreifen_vertikal, "flugstreifen") as Scursor:
        for row in Scursor:
            vertikale_stabilisatoren.append(row)

    # Alle Punkte die von vertikalen Streifen stammen werden gelöscht
    with arcpy.da.UpdateCursor(bildpunkte_extrahiert, ["img_name", "flugstreifen"]) as Ucursor:
        for row in Ucursor:
            flugstreifen = row[1]
            for stabilisator in vertikale_stabilisatoren:
                stabilisator_name_extracted = stabilisator[0]
                if stabilisator_name_extracted in flugstreifen:
                    Ucursor.deleteRow()


@func_info
def vertikale_flugstreifen_benoetigt(flugstreifen_horizontal: str, flugstreifen_vertikal: str,
                                     workspace_info: list) -> tuple:
    """
    Die Funktion ermittelt die Bereiche des Operates, in denen sich keine horizontalen Streifen befinden. Hier werden
    stattdessen die Punkte der vertikalen Streifen verwendet.
    Parameter:
        - flugstreifen_horizontal (str): Pfad zur Featureclass mit Flugstreifen in Ost-West-Ausdehnung
        - flugstreifen_vertikal (str): Pfad zur Featureclass mit Flugstreifen in Nord-Süd-Ausdehnung
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - vertikale_punkte_notwendig_bool (bool): ob Punkte von vertikalen Streifen benötigt werden
        - vertikal_streifen_bereich_inland (str): Bereich, in dem Punkte von vertikalen Streifen gehören
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # pfade zu temporären Featureclasses
    fc_meridianstreifen_buffer = rf"{speicherort}\meridianstreifen.gdb\meridianstreifen_{meridian}_buffer"
    fc_horizontal_buffer = rf"{fds_temp}\buffer_horizontal_{operat}"
    fc_horizontal_buffer_reduced = rf"{fds_temp}\buffer_horizontal_reduced_{operat}"
    fc_vertikal_buffer = rf"{fds_temp}\buffer_vertikal_{operat}"
    fc_vertikal_buffer_singlepart = rf"{fds_temp}\buffer_vertikal_singlepart_{operat}"
    fc_vertikal_buffer_reduced = rf"{fds_temp}\buffer_vertikal_reduced_{operat}"
    vertikal_streifen_bereich = rf"{fds_temp}\vertikal_streifen_bereich_{operat}"
    vertikal_streifen_bereich_inland = rf"{fds_temp}\vertikal_streifen_bereich_inland_{operat}"

    # horizontale Streifen puffern, dissolven und wieder negativ puffern (Fläche erstellen)
    arcpy.Buffer_analysis(flugstreifen_horizontal, fc_horizontal_buffer, "1500 Meters", dissolve_option="ALL")
    arcpy.Buffer_analysis(fc_horizontal_buffer, fc_horizontal_buffer_reduced, "-1150 Meters", dissolve_option="ALL")

    # vertikale Streifen puffern, dissolven und in Singleparts umwandeln
    arcpy.Buffer_analysis(flugstreifen_vertikal, fc_vertikal_buffer, "1500 Meters", dissolve_option="ALL")
    arcpy.MultipartToSinglepart_management(fc_vertikal_buffer, fc_vertikal_buffer_singlepart)

    # Erhalte anzahl an Linien innerhalb eines Pufferbereiches durch Spatial Join
    arcpy.SpatialJoin_analysis(target_features=fc_vertikal_buffer_singlepart, join_features=flugstreifen_vertikal,
                               out_feature_class=fc_vertikal_buffer_reduced, join_operation="JOIN_ONE_TO_ONE",
                               join_type="KEEP_ALL", field_mapping="", match_option="INTERSECT", search_radius="",
                               distance_field_name="")

    # Lösche Puffer, wenn weniger als 6 vertikale Linien in diesem Liegen, da dies wahrscheinlich Randstreifen sind
    with arcpy.da.UpdateCursor(fc_vertikal_buffer_reduced, ["Join_Count"]) as cursor:
        for row in cursor:
            if int(row[0]) < 6:
                cursor.deleteRow()

    # Ermittle Bereich, in dem die vertikalen Streifen benötigt werden
    arcpy.Erase_analysis(fc_vertikal_buffer_reduced, fc_horizontal_buffer_reduced, vertikal_streifen_bereich)
    arcpy.Clip_analysis(vertikal_streifen_bereich, fc_meridianstreifen_buffer, vertikal_streifen_bereich_inland)

    # Wenn keine Flächen mehr in Featureclass → False
    count = arcpy.GetCount_management(vertikal_streifen_bereich_inland)
    if count == 0:
        vertikale_punkte_notwendig_bool = False
        # arcpy.CopyFeatures_management(bildpunkte_extrahiert, finale_bildmittelpunkte)
    else:
        vertikale_punkte_notwendig_bool = True

    return vertikale_punkte_notwendig_bool, vertikal_streifen_bereich_inland


@func_info
def vertikale_flugstreifen_punkte_einfuegen(schraege_flugstreifen_liste: list, vertikal_streifen_bereich_inland: str,
                                            main_featureclasses_info: list, workspace_info: list):
    """
    Die Funktion fügt die benötigten Bildpunkte von vertikalen Flugstreifen ein.
    Parameter:
        - schraege_flugstreifen_liste (list): Liste mit schrägen Flugstreifen (potenzielle Talstreifen)
        - vertikal_streifen_bereich_inland (str): Bereich, in dem Punkte von vertikalen Streifen gehören
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    bildpunkte_vertikal = rf"{fds_temp}\bildpunkte_vertikal_{operat}"

    # Vertikale Punkte aus "bildpunkte_unbearbeitet" ausschneiden
    arcpy.Clip_analysis(bildpunkte_unbearbeitet, vertikal_streifen_bereich_inland, bildpunkte_vertikal)

    # bildpunkte aus "bildpunkte_vertikal" löschen, die von schrägen Streifen stammen
    with arcpy.da.UpdateCursor(bildpunkte_vertikal, ["flugstreifen"]) as cursor:
        for row in cursor:
            for flugstreifen in schraege_flugstreifen_liste:
                if row[0] in flugstreifen:
                    cursor.deleteRow()

    # Bildpunkte von vertikalen Streifen an "bildpunkte_extrahiert" anfügen
    arcpy.Append_management(bildpunkte_vertikal, bildpunkte_extrahiert)


@func_info
def punkte_talstreifen_ausschneiden(main_featureclasses_info: list, schraege_flugstreifen_liste: list,
                                    workspace_info: list):
    """
    Die Funktion löscht alle Bildpunkte, die sich im Bereich eines Talstreifens befinden und nicht Teil von diesem sind.
    Parameter:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - schraege_flugstreifen_liste (list): Liste mit schrägen Flugstreifen (potenzielle Talstreifen)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    talstreifen = rf"{fds_temp}\talstreifen_{operat}"

    # Erstelle Flugstreifen
    arcpy.PointsToLine_management(bildpunkte_extrahiert, talstreifen, Line_Field="flugstreifen", Close_Line="NO_CLOSE")

    # Speichere relevante Flugstreifen-Namen und lösche alle anderen aus "talstreifen"
    aktuelle_talstreifen_liste = []
    with arcpy.da.UpdateCursor(talstreifen, ["flugstreifen", "Shape_Length"]) as cursor:
        for row in cursor:
            if row[0] in schraege_flugstreifen_liste:
                aktuelle_talstreifen_liste.append(row[0])
                pass
            else:
                cursor.deleteRow()

    # Falls keine schrägen Streifen benötigt werden, ist count == 0
    count = arcpy.GetCount_management(talstreifen)
    if count == 0:
        return

    # Talstreifen werden gepuffert und alle Punkte ausgeschnitten, die sich innerhalb des Puffers befinden
    fc_schraege_flugstreifen_final_buffer = rf"{fds_temp}\schraege_flugstreifen_final_buffer_{operat}"
    fc_talstreifen_punkte_ausgeschnitten = rf"{fds_temp}\talstreifen_punkte_ausgeschnitten_{operat}"
    arcpy.Buffer_analysis(talstreifen, fc_schraege_flugstreifen_final_buffer, "200 Meters")
    arcpy.Clip_analysis(bildpunkte_extrahiert, fc_schraege_flugstreifen_final_buffer,
                        fc_talstreifen_punkte_ausgeschnitten)

    # Jene Punkte, die sich innerhalb des Talstreifen-Puffers befinden und nicht Teil eines Talstreifens sind, werden
    # an delete_list angefügt
    delete_list = []
    with arcpy.da.SearchCursor(fc_talstreifen_punkte_ausgeschnitten, ["img_name", "flugstreifen"]) as cursor:
        for row in cursor:
            if row[1] in aktuelle_talstreifen_liste:
                pass
            else:
                delete_list.append(row[0])

    # Punkte, die sich im Talstreifen-Bereich befinden aber nicht Teil eines Talstreifens sind, werden anhand von
    # delete_list gelöscht.
    with arcpy.da.UpdateCursor(bildpunkte_extrahiert, "img_name") as cursor:
        for row in cursor:
            if row[0] in delete_list:
                cursor.deleteRow()
