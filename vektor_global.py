# Dieses Python-Skript regelt alle globalen Vektor-Operationen, d.h. Vektor Operationen, die mehr als nur ein Operat
# betreffen, z.B. die Ermittlung der aktuellsten Fläche bei Überschneidungen und die Erstellung einer Featureclass
# mit den finalen Bildpunkten, die für die spätere Erstellung des Mosaic Datasets benötigt werden.
# Der Workflow wird durch das Starten von "main.py" initiiert, "vektor_global.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024

import arcpy
from info_wrapper import *
from statistics import mean
from time import time


@func_info
def operat_flaeche_erstellen(main_featureclasses_info, workspace_info) -> str:
    """
    Funktion erstellt die Operatsfläche des aktuellen Operates durch Pufferung der Bildpunkte.
    Parameter:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - operatsflaeche (str): Pfad zur Featureclass mit der erstellten Operatsfläche
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info

    # benötigte Pfade
    bildpunkte_buffer = rf"{fds_temp}\bildpunkte_buffer_{operat}"
    operatsflaeche = rf"{fds_temp}\operatsflaeche_{operat}"

    # Die Operatsfläche wird durch positive und negative Pufferung mit Dissolving erstellt
    arcpy.PairwiseBuffer_analysis(bildpunkte_extrahiert, bildpunkte_buffer, "1600 Meters", dissolve_option="ALL")
    arcpy.PairwiseBuffer_analysis(bildpunkte_buffer, operatsflaeche, "-1450 Meters", dissolve_option="ALL")

    # Das Feld Operat wird in der fc "operatsflaeche" erstellt und mit der aktuellen Operatsnummer befüllt
    arcpy.AddField_management(operatsflaeche, "operat", "TEXT")
    with arcpy.da.UpdateCursor(operatsflaeche, "operat") as cursor:
        for row in cursor:
            cursor.updateRow([operat])

    return operatsflaeche


@func_info
def flaechen_sammlung_befuellen(operatsflaeche: str, global_info: list, workspace_info: list):
    """
    Funktion fügt aktuelle Operatsfläche an die Featureclass 'flaechen_sammlung' an, falls die Operatsfläche
    bereits in 'flaechen_collection' vorhanden war, die alte Fläche gelöscht. Der Zeitpunkt des Hinzufügens und das
    Flugjahr des Operates werden in Attributen gespeichert.
    Parameter:
        - operatsflaeche (str): Pfad zur Featureclass mit der erstellten Operatsfläche
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # Ist das Operat in "flaechen_sammlung" vorhanden, wird es gelöscht
    with arcpy.da.UpdateCursor(flaechen_sammlung, "operat_nr") as cursor:
        for row in cursor:
            if row[0] == operat:
                cursor.deleteRow()

    # Das aktuelle Operat wird in "input_operat" gespeichert
    input_operat = []
    with arcpy.da.SearchCursor(operatsflaeche, ["operat", "SHAPE@"]) as cursor:
        for row in cursor:
            input_operat.append(row)

    # Das Operat wird in "flaechen_sammlung" hinzugefügt, mit Zeitpunkt des Hinzufügens und Flugjahr des Operates
    with arcpy.da.InsertCursor(flaechen_sammlung, ["operat_nr", "SHAPE@", "jahr", "zeitpunkt"]) as cursor:
        for row in input_operat:
            operat_nr = row[0]
            zeitpunkt = time()
            shape = row[1]
            jahr = str(operat_nr[0:4])
            cursor.insertRow([operat_nr, shape, jahr, zeitpunkt])


@func_info
def operat_ueberschneidungen(global_info: list) -> str:
    """
    Funktion erstellt die Featureclass "kombininierte_operat_ueberschneidungen", in der die Geometrie der
    Überschneidung und Informationen zu den schneidenden Operaten (inklusive Flugjahr und Lade-Zeitpunkt) gespeichert
    sind.
    Parameter:
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
    Rückgabewert:
        - kombininierte_operat_ueberschneidungen (str): Pfad zu Featureclass mit Geometrie der Überschneidung und
                                                        Informationen zu den schneidenden Operaten
    """

    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # benötigte Pfade
    flaechen_ueberschneidungen = f"{fds_temp_global}\\flaechen_ueberschneidungen"
    flaechen_ueberschneidungen_singlepart = f"{fds_temp_global}\\flaechen_ueberschneidungen_singlepart"
    einzelne_flaechen_ueberschneidungen = f"{fds_temp_global}\\einzelne_flaechen_ueberschneidungen"
    kombininierte_operat_ueberschneidungen = f"{fds_temp_global}\\kombininierte_operat_ueberschneidungen"

    # Flächen schneiden → mehrere überlagernde multipart Flächen
    arcpy.Intersect_analysis(flaechen_sammlung, flaechen_ueberschneidungen)
    # mehrere überlagernde singlepart Flächen
    arcpy.MultipartToSinglepart_management(flaechen_ueberschneidungen, flaechen_ueberschneidungen_singlepart)
    # Überlagernde Flächen dissolven → keine Information, nur Überschneidungsflächen
    arcpy.PairwiseDissolve_analysis(in_features=flaechen_ueberschneidungen_singlepart,
                                    out_feature_class=einzelne_flaechen_ueberschneidungen,
                                    dissolve_field=["Shape_Area"],
                                    statistics_fields=[],
                                    multi_part="SINGLE_PART",
                                    concatenation_separator="")
    # Information zu Überschneidungsflächen hinzufügen; Attribute "operat_nr", "jahr" und "zeitpunkt" der einzelnen
    # überlagernden Flächen verkettet auf im vorigen Schritt erstellte Fläche übertragen
    arcpy.SpatialJoin_analysis(target_features=einzelne_flaechen_ueberschneidungen,
                               join_features=flaechen_ueberschneidungen_singlepart,
                               out_feature_class=kombininierte_operat_ueberschneidungen,
                               join_operation="JOIN_ONE_TO_ONE",
                               join_type="KEEP_ALL",
                               field_mapping=f"operat_nr \"operat_nr\" true true false 255 Text 0 0,Join,\";\",{flaechen_ueberschneidungen_singlepart},operat_nr,0,255;jahr \"jahr\" true true false 255 Text 0 0,Join,\";\",{flaechen_ueberschneidungen_singlepart},jahr,0,255;zeitpunkt \"zeitpunkt\" true true false 255 Text 0 0,Join,\";\",{flaechen_ueberschneidungen_singlepart},zeitpunkt,0,255",
                               match_option="ARE_IDENTICAL_TO",
                               search_radius="",
                               distance_field_name="")

    return kombininierte_operat_ueberschneidungen


@func_info
def aktuelle_operate_extrahieren(kombininierte_operat_ueberschneidungen: str, global_info: list,
                                 workspace_info: list) -> tuple:
    """
    Die Funktion liest die verketteten Informationen aus "kombininierte_operat_ueberschneidungen" aus.
    Anhand des Attributes Jahr wird die Überschneidungsfläche dem neusten Operat zugeordnet. Sollten das Jahr gleich
    sein, wird das neuer-geladene Operat anhand des Attributes "zeitpunkt" als richtiges Operat angenommen.
    Die Listen "zu_input_anfuegen" und "nicht_zu_input_anfuegen" liefern Information in Bezug auf das Input-Operat.
    Parameter:
        - kombininierte_operat_ueberschneidungen (str): Pfad zu Featureclass mit Geometrie der Überschneidung und
                                                        Informationen zu den schneidenden Operaten
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewerte (tuple):
        - zu_input_anfuegen (list): Überschneidungen, die dem Input Operat angefügt werden sollen
        - nicht_zu_input_anfuegen (list): Überschneidungen, die nicht dem Input Operat angefügt werden sollen
        - extrahierte_operat_ueberschneidungen (str): Pfad zu Featureclass mit korrekt zugeordneten Überschneidungen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # benötigter Pfad
    extrahierte_operat_ueberschneidungen = f"{fds_temp_global}\\extrahierte_operat_ueberschneidungen"

    # kopiere "kombininierte_operat_ueberschneidungen"
    arcpy.CopyFeatures_management(kombininierte_operat_ueberschneidungen, extrahierte_operat_ueberschneidungen)

    # Jene Überschneidungen, die dem Input Operat angefügt werden
    zu_input_anfuegen = []
    # Jene Überschneidungen, die nicht dem Input Operat angefügt werden
    nicht_zu_input_anfuegen = []

    with arcpy.da.UpdateCursor(extrahierte_operat_ueberschneidungen,
                               ["operat_nr", "jahr", "zeitpunkt", "SHAPE@"]) as cursor:
        for row in cursor:
            # verkettete operatsnamen aufspalten
            operatsnamen = row[0].split(";")
            # verkettete jahre aufspalten
            jahre_input = row[1].replace(",", ".").split(";")
            jahre = []
            for x in jahre_input:
                jahr = float(x)
                jahre.append(jahr)
            # maximales Flugjahr und durchschnittliches Flugjahr ermitteln
            jahr_max = max(jahre)
            jahr_mean = mean(jahre)
            # besitzen mehrere Operate dasselbe (aktuellste) Flugjahr?
            quantity_jahr_max = 0
            for item in jahre:
                if item == jahr_max:
                    quantity_jahr_max += 1
            # Lade-Zeitpunkte der Operate ermitteln und aktuellstes Operat
            zeitpunkte_input = row[2].replace(",", ".").split(";")
            zeitpunkte = []
            for x in zeitpunkte_input:
                zeitpunkt = float(x)
                zeitpunkte.append(zeitpunkt)
            zeitpunkt_max = max(zeitpunkte)

            if jahr_max == jahr_mean:
                # bei Operaten des gleichen Flugjahres wird das aktueller geladene gewählt
                stelle_mit_korrekter_info = zeitpunkte.index(zeitpunkt_max)
            else:
                if quantity_jahr_max == 1:
                    # aktuellstes Flugjahr kommt nur einmal vor
                    stelle_mit_korrekter_info = jahre.index(jahr_max)
                else:
                    # aktuellstes flugjahr kommt mehrmals vor, ältere flugjahre existieren auch
                    multiple_max_values = []
                    count = 0
                    # das am neuesten reingeladene operat von den operaten mit aktuellstem flugjahr wird ermittelt
                    for item in jahre:
                        if item == jahr_max:
                            x = zeitpunkte[count]
                            multiple_max_values.append(x)
                        count += 1
                    max_multiple_max_values = max(multiple_max_values)
                    stelle_mit_korrekter_info = zeitpunkte.index(max_multiple_max_values)

            if operat in operatsnamen:
                if operat == operatsnamen[stelle_mit_korrekter_info]:
                    # Jene Überschneidungen, die dem Input Operat angefügt werden
                    zu_input_anfuegen.append(row)
                else:
                    # Jene Überschneidungen, die nicht dem Input Operat angefügt werden
                    nicht_zu_input_anfuegen.append(row)
            else:
                # Jene, die nichts mit dem Input Operat zu tun haben werden ignoriert
                pass

            # update Überschneidungsflächen mit korrekter Information
            cursor.updateRow([operatsnamen[stelle_mit_korrekter_info],
                              jahre[stelle_mit_korrekter_info],
                              zeitpunkte[stelle_mit_korrekter_info], row[3]])

    return zu_input_anfuegen, nicht_zu_input_anfuegen, extrahierte_operat_ueberschneidungen


@func_info
def flaechen_sammlung_zusammenfuegen(extrahierte_operat_ueberschneidungen: str, global_info: list,
                                     workspace_info: list) -> tuple:
    """
    Die Funktion erstellt die Featureclass mit den korrekt zugeordneten Überschneidungsflächen durch Dissolving der
    Überschneidungsflächen mit den übrigen Operatsflächen.
    Parameter:
        - extrahierte_operat_ueberschneidungen (str): Pfad zu Featureclass mit korrekt zugeordneten Überschneidungen
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewerte (tuple):
        - flaechen_sammlung_final (str): Pfad zur fc mit allen korrekt zugeordneten Operaten
        - input_operat_ohne_ueberschneidungen (List): Liste der aktuellen Operatsfläche ohne Überschneidungsflächen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # benötigte Pfade
    operat_ueberschneidungen_ausgeschnitten = rf"{fds_temp_global}\operat_ueberschneidungen_ausgeschnitten"
    flaechen_sammlung_final = rf"{fds_output_global}\flaechen_sammlung_final"

    # Überschneidungen rauslöschen
    arcpy.Erase_analysis(flaechen_sammlung, extrahierte_operat_ueberschneidungen,
                         operat_ueberschneidungen_ausgeschnitten)

    # Das neue Operat ohne Überschneidungsflächen separat speichern
    input_operat_ohne_ueberschneidungen = []
    with arcpy.da.SearchCursor(operat_ueberschneidungen_ausgeschnitten,
                               ["operat_nr", "jahr", "zeitpunkt", "SHAPE@"]) as cursor:
        for row in cursor:
            # aktuelles Operat
            if row[0] == operat:
                input_operat_ohne_ueberschneidungen.append(row)

    # Die Operatsflächen komplettieren durch Dissolve von Flächen ohne Überschneidung und Überschneidungsflächen
    arcpy.Append_management(extrahierte_operat_ueberschneidungen, operat_ueberschneidungen_ausgeschnitten,
                            schema_type="NO_TEST")
    arcpy.Dissolve_management(operat_ueberschneidungen_ausgeschnitten, flaechen_sammlung_final,
                              dissolve_field="operat_nr")
    return flaechen_sammlung_final, input_operat_ohne_ueberschneidungen


@func_info
def input_operat_aufteilen(zu_input_anfuegen: list, input_operat_ohne_ueberschneidungen: list,
                           global_info: list) -> tuple:
    """
    Die Funktion teilt das Operat auf 2 Featureclasses auf. In "fc_zu_input_anfuegen" landen die Überschneidungen des
    Input-Operates, bei denen in weiterer Folge die Punkte des anderen Operates gelöscht werden müssen, damit dann die
    Punkte des Input-Operates hinzugefügt werden können. In "fc_input_operat_ohne_ueberschneidungen" befinden sich die
    Flächen, bei welchen keine alten Punkte ausgeschnitten, sondern einfach nur die aktuellen Punkte eingefügt werden.
    Parameter:
        - zu_input_anfuegen (list): Überschneidungen, die dem Input Operat angefügt werden sollen
        - input_operat_ohne_ueberschneidungen (List): Liste der aktuellen Operatsfläche ohne Überschneidungsflächen
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
    Rückgabewerte (tuple):
        - fc_zu_input_anfuegen (str): Featureclass, die die Überschneidungsflächen des Input-Operates enthält,
                                      bei denen die Bildpunkte hinzugefügt werden sollen
        - fc_input_operat_ohne_ueberschneidungen (str): Pfad der aktuellen Operatsfläche ohne Überschneidungsflächen
    """

    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # Featureclass, die jene Überschneidungsflächen des aktuellen Operates enthalten, bei denen die Punkte hinzugefügt
    # werden sollen
    fc_zu_input_anfuegen = arcpy.CreateFeatureclass_management(fds_temp_global, "fc_zu_input_anfuegen", "POLYGON")
    arcpy.AddFields_management(fc_zu_input_anfuegen, [["operat", "TEXT"], ["jahr", "TEXT"], ["zeitpunkt", "TEXT"]])

    # alle Features vom letzten Durchlauf werden entfernt
    with arcpy.da.UpdateCursor(fc_zu_input_anfuegen, ["operat", "jahr", "zeitpunkt", "SHAPE@"]) as cursor:
        for row in cursor:
            cursor.deleteRow()

    # Überschneidungen, die dem aktuellen Operat hinzugefügt werden sollen, einfügen
    with arcpy.da.InsertCursor(fc_zu_input_anfuegen, ["operat", "jahr", "zeitpunkt", "SHAPE@"]) as cursor:
        for item in zu_input_anfuegen:
            cursor.insertRow(item)

    # Featureclass, die das Input-Operat ohne Überschneidungsflächen beinhaltet
    fc_input_operat_ohne_ueberschneidungen = \
        arcpy.CreateFeatureclass_management(fds_temp_global, "fc_input_operat_ohne_ueberschneidungen", "POLYGON")
    arcpy.AddFields_management(fc_input_operat_ohne_ueberschneidungen,
                               [["operat", "TEXT"], ["jahr", "TEXT"], ["zeitpunkt", "TEXT"]])

    # alle Features vom letzten Durchlauf werden entfernt
    with arcpy.da.UpdateCursor(fc_input_operat_ohne_ueberschneidungen, ["operat", "jahr", "zeitpunkt", "SHAPE@"]) \
            as cursor:
        for row in cursor:
            cursor.deleteRow()

    # Input-Operat ohne Überschneidungen einfügen
    with arcpy.da.InsertCursor(fc_input_operat_ohne_ueberschneidungen, ["operat", "jahr", "zeitpunkt", "SHAPE@"]) \
            as cursor:
        for element in input_operat_ohne_ueberschneidungen:
            cursor.insertRow(element)

    return fc_zu_input_anfuegen, fc_input_operat_ohne_ueberschneidungen


@func_info
def punkte_ausschneiden_hinzufuegen(fc_zu_input_anfuegen: str, fc_input_operat_ohne_ueberschneidungen: str,
                                    global_info: list, main_featureclasses_info: list) -> tuple:
    """
    Die Funktion fügt alle korrekten Punkte in "punkte_sammlung" zusammen und erstellt 2 Listen, die die gelöschten bzw.
    neu hinzugefügten Namen der Bildpunkte enthalten
    Parameter:
        - fc_zu_input_anfuegen (str): Featureclass, die die Überschneidungsflächen des Input-Operates enthält,
                                      bei denen die Bildpunkte hinzugefügt werden sollen
        - fc_input_operat_ohne_ueberschneidungen (str): Pfad der aktuellen Operatsfläche ohne Überschneidungsflächen
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
    Rückgabewerte (tuple):
        - loesch_punkte_liste (list): Liste mit allen Punkten die aus "punkte_sammlung" entfernt wurden
        - hinzugefuegt_punkte_liste (list): Liste mit allen Punkten, die in "punkte_sammlung" hinzugefügt wurden
    """

    bildpunkte_unbearbeitet, bildpunkte_extrahiert = main_featureclasses_info
    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # benötigte Pfade
    punkte_sammlung_unfertig = rf"{fds_temp_global}\punkte_sammlung_unfertig"
    punkte_input_operat_ueberschneidungen = rf"{fds_temp_global}\punkte_input_operat_ueberschneidungen"
    punkte_input_operat_ohne_ueberschneidungen = rf"{fds_temp_global}\punkte_input_operat_ohne_ueberschneidungen"
    loesch_punkte = rf"{fds_temp_global}\loesch_punkte"

    # fc wird angepasst
    arcpy.AlterField_management(bildpunkte_extrahiert, "operat", new_field_name="operat_nr")

    # Erstelle Featureclass mit Punkten, die gelöscht werden sollen
    arcpy.PairwiseClip_analysis(punkte_sammlung, fc_zu_input_anfuegen, loesch_punkte)

    # Liste mit allen Punkten die aus Mosaic Dataset gelöscht werden sollen
    loesch_punkte_liste = []
    with arcpy.da.SearchCursor(loesch_punkte, ["img_name", "operat_nr"]) as cursor:
        for row in cursor:
            abgleich = row[0] + row[1]
            loesch_punkte_liste.append(abgleich)

    # aus "punkte_sammlung_unfertig" werden die Punkte gelöscht, anstelle deren jene des Input-Operates hinkommen
    arcpy.PairwiseErase_analysis(punkte_sammlung, fc_zu_input_anfuegen, punkte_sammlung_unfertig)
    # Die Punkte, welche vom Input stammen und in den Überschneidungsflächen liegen werden ermittelt
    arcpy.PairwiseClip_analysis(bildpunkte_extrahiert, fc_zu_input_anfuegen, punkte_input_operat_ueberschneidungen)
    # Die korrekten Punkte der Überschneidungsflächen werden eingefügt
    arcpy.Append_management(punkte_input_operat_ueberschneidungen, punkte_sammlung_unfertig)

    # Die "punkte_input_operat_ohne_ueberschneidungen" werden aus den Punkten von "bildpunkte_extrahiert" ausgeschnitten
    arcpy.PairwiseClip_analysis(bildpunkte_extrahiert, fc_input_operat_ohne_ueberschneidungen,
                                punkte_input_operat_ohne_ueberschneidungen)
    # Da hier keine Punkte in der "punkte_sammlung" liegen, können die Punkte des Input Operates ohne Überschneidung
    # einfach eingefügt werden
    arcpy.Append_management(punkte_input_operat_ohne_ueberschneidungen, punkte_sammlung_unfertig)

    # Liste mit allen Punkten, die hinzugefügt wurden
    hinzugefuegt_punkte_liste = []
    # bei Überschneidungen
    with arcpy.da.SearchCursor(punkte_input_operat_ohne_ueberschneidungen, "img_name") as cursor:
        for row in cursor:
            hinzugefuegt_punkte_liste.append(row[0])
    # alles außer Überschneidungen
    with arcpy.da.SearchCursor(punkte_input_operat_ueberschneidungen, "img_name") as cursor:
        for row in cursor:
            hinzugefuegt_punkte_liste.append(row[0])

    # "punkte_sammlung" wird aktualisiert
    arcpy.DeleteFeatures_management(punkte_sammlung)
    arcpy.Append_management(punkte_sammlung_unfertig, punkte_sammlung)

    return loesch_punkte_liste, hinzugefuegt_punkte_liste


@func_info
def ausland_operate_bestimmen(flaechen_sammlung_final: str, global_info: list, workspace_info: list) -> list:
    """
    Alle Operate, die zur Gänze ausserhalb von Ö liegen werden aus "flaechen_sammlung_final" gelöscht und die
    Operats-Nummer wird in einer Liste gespeichert.
    Parameter:
        - flaechen_sammlung_final (str): Pfad zur fc mit allen korrekt zugeordneten Operaten
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewerte:
        - operate_ausserhalb (list): Liste von Operaten, die zur Gänze ausserhalb von Ö liegen
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    geodatabase_global, fds_output_global, fds_temp_global, flaechen_sammlung, punkte_sammlung = global_info

    # benötigte Pfade
    meridianflaeche_gepuffert = rf"{speicherort}\meridianstreifen.gdb\meridianstreifen_{meridian}_buffer"
    operate_ausland = rf"{fds_temp_global}\operate_ausland"

    # Lösche Daten vom letzten Durchlauf
    arcpy.Delete_management(operate_ausland)

    # Wähle alle Operate die zur gänze außerhalb von Österreich liegen aus
    arcpy.MakeFeatureLayer_management(flaechen_sammlung_final, operate_ausland)
    arcpy.SelectLayerByLocation_management(operate_ausland, "INTERSECT_3D", meridianflaeche_gepuffert,
                                           None, "NEW_SELECTION", "INVERT")

    # Füge alle Operats-Nummern der Liste "operat_ausserhalb" hinzu, diese müssen gelöscht werden
    operate_ausserhalb = []
    try:
        with arcpy.da.SearchCursor(operate_ausland, ["operat_nr"]) as cursor:
            for row in cursor:
                operate_ausserhalb.append(row[0])
    except:
        print("keine Flächen außerhalb gefunden!")
    # lösche Operate, die nur im Ausland liegen
    arcpy.DeleteRows_management(operate_ausland)
    return operate_ausserhalb
