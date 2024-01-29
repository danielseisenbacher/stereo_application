# Dieses Python-Skript ermittelt alle User-Inputs und erstellt bzw. konfiguriert den Workspace, inklusive nötigen
# Geodatabases, Featuredatasets und Featureclasses.
# Der Workflow wird durch das Starten von "main.py" initiiert, "workspace_funktionen.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024

import os
import arcpy
from info_wrapper import *


@func_info
def meridian_abfragen() -> str:
    """
    Funktion fragt den Meridian des Operates ab, welches bearbeitet werden soll.
    Rückgabewert:
        - meridian (str): Meridian-Bezeichnung
    """

    while True:
        meridian = input("In welchem Meridian befindet sich das Operat? (M28, M31, M34)\n")
        if meridian in ["M28", "M31", "M34"]:
            return meridian
        else:
            print("Error: Korrigieren Sie die Eingabe")
            continue


@func_info
def operat_abfragen() -> str:
    """
    Funktion fragt die Operatsnummer des Operates ab, welches bearbeitet werden soll.
    Rückgabewert:
        - operat (str): Operatsnummer
    """

    while True:
        operat = input("Welches Operat soll berechnet werden? (z.B. 2020550)\n")
        try:
            int(operat)
            return operat
        except:
            print("Error: Korrigieren Sie die Eingabe")
            continue


@func_info
def workspace_info_konfigurieren(meridian: str, operat: str, speicherort: str) -> list:
    """
    Funktion erstellt Aufbau des Datei-Verzeichnisses + wichtige Kennzahlen (Meridian, EPSG, Operat).
    Parameter:
        - meridian (str): Meridian-Bezeichnung
        - operat (str): Operatsnummer
        - speicherort (str): Pfad des Speicherortes
    Rückgabewert:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """
    # EPSG Nummer wird ermittelt
    if meridian == "M28":
        epsg = 31254
    elif meridian == "M31":
        epsg = 31255
    else:
        epsg = 31256

    meridian_ordner = rf"{speicherort}\{meridian}"
    os.makedirs(meridian_ordner, exist_ok=True)                 # Meridian-Ordner erstellen

    operat_ordner = rf"{meridian_ordner}\{operat}"
    os.makedirs(operat_ordner, exist_ok=True)                   # Operat-Ordner erstellen

    gdb = rf"{operat_ordner}\{operat}.gdb"
    arcpy.CreateFileGDB_management(operat_ordner, operat)       # Geodatabase erstellen

    fds_final = rf"{gdb}\output"
    arcpy.CreateFeatureDataset_management(gdb, "output", epsg)  # "output" Featuredataset erstellen

    fds_temp = rf"{gdb}\temp"
    arcpy.CreateFeatureDataset_management(gdb, "temp", epsg)    # "temp" Featuredataset erstellen

    # kompakte Liste mit Informationen zu Workspace
    workspace_info = [meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp]

    return workspace_info


@func_info
def featureclasses_erstellen(workspace_info: list) -> list:
    """
    Funktion erstellt die Featureclasses "bildpunkte_unbearbeitet_{operat}" und "bildpunkte_extrahiert_{operat}" im
    Featuredataset "final".
    Parameter:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - main_featureclasses_info (list): Pfade zu den wichtigsten Featureclasses
                                           (bildpunkte_unbearbeitet, bildpunkte_extrahiert)
    """

    [meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp] = workspace_info

    # Featureclass "bildpunkte_unbearbeitet_{operat}" wird erstellt und Field Design angepasst
    bildpunkte_unbearbeitet = arcpy.CreateFeatureclass_management(
        fds_final,
        f"bildpunkte_unbearbeitet_{operat}",
        "POINT"
    )
    feld_design = [["operat", "TEXT"], ["img_name", "TEXT"], ["flugstreifen", "TEXT"], ["flughoehe", "TEXT"]]
    arcpy.AddFields_management(bildpunkte_unbearbeitet, field_description=feld_design)

    # Featureclass "bildpunkte_extrahiert_{operat}" mit gleichem Design wird erstellt
    bildpunkte_extrahiert = rf"{fds_final}\bildpunkte_extrahiert_{operat}"
    arcpy.Copy_management(bildpunkte_unbearbeitet, bildpunkte_extrahiert)

    # kompakte Liste aus Pfaden zu den wichtigsten Featureclasses
    main_featureclasses_info = [bildpunkte_unbearbeitet, bildpunkte_extrahiert]
    return main_featureclasses_info


@func_info
def meridianstreifen_gdb_erstellen(workspace_info: list, meridianstreifen_pfad: str) -> tuple:
    """
    Funktion erstellt die Geodatabase "meridianstreifen.gdb", welche alle korrekt projizierten Meridianstreifen und
    einen Puffer von +250 Meter der Fläche Österreichs enthält.
    Parameter:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
        - meridianstreifen_pfad (str): Pfade zur externen Meridianstreifen_Featureclass, die kopiert werden soll
    Rückgabewert (tuple):
        - merdianstreifen (str):    Pfad zu Meridianstreifen Featureclass
        - oesterreich_buffer (str): Pfad zur Featureclass mit gepuffert Fläche von Österreich
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Meridianstreifen Geodatabase Pfade
    meridianstreifen_gdb = rf"{speicherort}\meridianstreifen.gdb"
    oesterreich_buffer = rf"{meridianstreifen_gdb}\oesterreich_buffer"

    meridianstreifen_gdb_existiert = arcpy.Exists(meridianstreifen_gdb)

    if not meridianstreifen_gdb_existiert:
        # Meridianstreifen Geodatabase existiert noch nicht
        arcpy.CreateFileGDB_management(speicherort, f"meridianstreifen")
        meridianstreifen_unbearbeitet = rf"{meridianstreifen_gdb}\meridianstreifen_unbearbeitet"

        # Meridianstreifen werden von "meridianstreifen_pfad" kopiert
        arcpy.CopyFeatures_management(meridianstreifen_pfad, meridianstreifen_unbearbeitet)

        meridianstreifen = [[rf"{meridianstreifen_gdb}\meridianstreifen_M28", 28, 31254],
                            [rf"{meridianstreifen_gdb}\meridianstreifen_M31", 31, 31255],
                            [rf"{meridianstreifen_gdb}\meridianstreifen_M34", 34, 31256]]

        for elem in meridianstreifen:
            # einzelne Meridianstreifen Featureclasses werden erstellt
            temp_layer = rf"{meridianstreifen_gdb}\temp_layer"
            temp_fc = rf"{meridianstreifen_gdb}\temp_layer_{elem[1]}"

            # Meridianstreifen wird kopiert und korrekt projiziert
            arcpy.MakeFeatureLayer_management(meridianstreifen_unbearbeitet, temp_layer, f"MERIDIAN = {elem[1]}")
            arcpy.CopyFeatures_management(temp_layer, temp_fc)
            arcpy.Project_management(temp_fc, elem[0], out_coor_system=elem[2])

            # Meridianstreifen wird gepuffert
            arcpy.PairwiseBuffer_analysis(elem[0], f"{elem[0]}_buffer", "250 Meters")

            # temporäre Featureclasses werden gelöscht
            arcpy.Delete_management([temp_layer, temp_fc])

        # Featureclass mit gepufferter Fläche von Österreich wird erstellt
        arcpy.PairwiseBuffer_analysis(meridianstreifen_unbearbeitet, oesterreich_buffer, "250 Meters",
                                      dissolve_option="ALL")

    # Rückgabe des aktuellen Meridianstreifen-Pfades
    meridianstreifen = rf"{meridianstreifen_gdb}\meridianstreifen_{meridian}"
    return meridianstreifen, oesterreich_buffer


@func_info
def global_gdb_erstellen(workspace_info: list) -> list:
    """
    Funktion erstellt alle nötigen Featureclasses, Featuredatasets und eine Geodatabase, die für die Zusammenführung
    der Operate benötigt werden.
    Parameter:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewert:
        - global_info (list): Liste aus Pfaden zu gdb, fds und fc für die Zusammenführung der Operate
    """

    # Die nötigen Pfade definieren
    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info
    geodatabase_global = rf"{speicherort}\{meridian}_global.gdb"
    fds_output_name = "output"
    fds_output = rf"{geodatabase_global}\{fds_output_name}"
    fds_temp_name = "temp"
    fds_temp = rf"{geodatabase_global}\{fds_temp_name}"
    flaechen_sammlung_name = "flaechen_sammlung"
    flaechen_sammlung = rf"{fds_output}\{flaechen_sammlung_name}"
    punkte_sammlung_name = "punkte_sammlung"
    punkte_sammlung = rf"{fds_output}\{punkte_sammlung_name}"

    arcpy.env.workspace = geodatabase_global

    # Erstellung der gdb, fds, fc
    geodatabase_global_existiert = os.path.exists(geodatabase_global)
    if geodatabase_global_existiert:
        print("gdb existiert bereits")
        pass
    else:
        print("gdb wird erstellt")
        arcpy.CreateFileGDB_management(speicherort, f"{meridian}_global")

    datasets = arcpy.ListDatasets()
    if fds_output_name in datasets:
        print("fds existiert bereits")
        pass
    else:
        print("fds wird erstellt")
        arcpy.CreateFeatureDataset_management(geodatabase_global, "output", epsg)

    if fds_temp_name in datasets:
        print("fds existiert bereits")
        pass
    else:
        print("fds wird erstellt")
        arcpy.CreateFeatureDataset_management(geodatabase_global, "temp", epsg)

    featureclasses = arcpy.ListFeatureClasses(feature_dataset=fds_output_name)
    if flaechen_sammlung_name in featureclasses:
        print("fc existiert bereits")
        pass
    else:
        print("fc wird erstellt")
        flaechen_sammlung = arcpy.CreateFeatureclass_management(fds_output, "flaechen_sammlung", "POLYGON")
        arcpy.AddFields_management(flaechen_sammlung, [["operat_nr", "TEXT"], ["jahr", "TEXT"], ["zeitpunkt", "TEXT"]])

    if punkte_sammlung_name in featureclasses:
        print("fc existiert bereits")
        pass
    else:
        print("fc wird erstellt")
        punkte_sammlung = arcpy.CreateFeatureclass_management(fds_output, "punkte_sammlung", "POINT")
        arcpy.AddFields_management(punkte_sammlung, [["img_name", "TEXT"], ["operat_nr", "TEXT"],
                                                     ["flugstreifen", "TEXT"], ["flughoehe", "TEXT"]])

    global_info = [geodatabase_global, fds_output, fds_temp, flaechen_sammlung, punkte_sammlung]
    return global_info
