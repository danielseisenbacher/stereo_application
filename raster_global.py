# Dieses Python-Skript erledigt das Erstellen des Mosaic Datasets, bzw. das Befüllen und Aussortieren von
# ausgewählten Rastern.
# Der Workflow wird durch das Starten von "main.py" initiiert, "raster_global.py" kann vom User ignoriert werden.

# Autor: Daniel Seisenbacher
# Interpreter: Python 3.9 (arcgispro-py3)
# Datum: 20. Jänner 2024

import arcpy
from info_wrapper import *


@func_info
def raster_workspace_erstellen(workspace_info: list) -> str:
    """
    Eine Geodatabase und ein Mosaicdataset wird erstellt, in dem sich das Mosaic Dataset befindet.
    Parameter:
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    Rückgabewerte (tuple):
        - mosaic_dataset (str): Pfad zum Mosaic Dataset mit allen Bildern des Meridians
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # Erstelle Mosaic Geodatabase
    mosaic_gdb = rf"{speicherort}\{meridian}_mosaic.gdb"
    mosaic_gdb_existiert = arcpy.Exists(mosaic_gdb)
    if not mosaic_gdb_existiert:
        mosaic_gdb = arcpy.CreateFileGDB_management(speicherort, f"{meridian}_mosaic")
        print("mosaic gdb wrd erstellt")
        return mosaic_gdb

    # Erstelle Mosaic Dataset
    mosaic_dataset = rf"{mosaic_gdb}\mosaic"
    mosaic_existiert = arcpy.Exists(mosaic_dataset)
    if not mosaic_existiert:
        mosaic_dataset = arcpy.CreateMosaicDataset_management(mosaic_gdb, "mosaic", coordinate_system=epsg)
        print("Mosaic Dataset wird erstellt")
        arcpy.AddFields_management(mosaic_dataset, [["abgleich", "TEXT"], ["operat_nr", "TEXT"]])

    return mosaic_dataset


@func_info
def bilder_aus_mosaic_entfernen(mosaic_dataset: str, loesch_punkte_liste: list):
    """
    Die Funktion löscht alle bereits im Mosaic Dataset befindlichen Raster, die einem Namen aus "loesch_punkte_liste"
    entsprechen.
    Parameter:
        - mosaic_dataset (str): Pfad zum Mosaic Dataset mit allen Bildern des Meridians
        - loesch_punkte_liste (list): Liste mit allen Punkten die aus "punkte_sammlung" entfernt wurden
    """

    loesch_punkte_tuple = tuple(loesch_punkte_liste)

    # Lösche Raster, falls dies nötig ist
    if len(loesch_punkte_tuple) > 0:
        sql_statement = f"abgleich IN {loesch_punkte_tuple}"
        arcpy.RemoveRastersFromMosaicDataset_management(
            mosaic_dataset,
            sql_statement,
            "UPDATE_BOUNDARY",
            "MARK_OVERVIEW_ITEMS",
            "DELETE_OVERVIEW_IMAGES",
            "DELETE_ITEM_CACHE",
            "REMOVE_MOSAICDATASET_ITEMS",
            "UPDATE_CELL_SIZES"
        )


@func_info
def raster_zu_mosaic_hinzufuegen(mosaic_dataset: str, prj_dateien: list, dgm_pfad: str, workspace_info: list):
    """
    Mithilfe der Arcpy Funktion "AddRastersToMosaicDataset_management" werden alle Raster eingefügt, deren Pfad in
    der .prj-Datei korrekt angepasst wurden (alle Raster, die benötigt werden), der Rest wird ignoriert.
    Das DGM ermöglicht Terrain Following (Automatisches Anpassen des Fokus im Bildmittelpunkt).
    Parameter:
        - mosaic_dataset (str): Pfad zum Mosaic Dataset mit allen Bildern des Meridians
        - prj_dateien (list): Liste mit Pfad(en) zu prj-Datei(en)
        - dgm_pfad (str): Pfad zum digitalen Geländemodell
        - workspace_info (list): Liste aus Informationen zum Workspace
                                 (Meridian, Operatsnummer, Pfade, epsg-Nummer)
    """

    meridian, epsg, operat, speicherort, meridian_ordner, operat_ordner, gdb, fds_final, fds_temp = workspace_info

    # For Schleife, falls mehrere .prj-Dateien ausgelesen werden
    for item in prj_dateien:
        # Die ausgewählten Bilder werden hinzugefügt
        raster_art = "Match-AT"
        print("\nDas Mosaic Dataset wird befüllt...")
        print(item)
        value_table = arcpy.ValueTable(2)
        value_table.addRow(["DEM", dgm_pfad])

        try:
            # Raster werden eingefügt
            arcpy.AddRastersToMosaicDataset_management(
                mosaic_dataset,
                raster_art,
                item,
                aux_inputs=value_table,
                spatial_reference=epsg,
                )

        except:
            print("kein Bild aus sub_Operat wurde ausgewählt")
        print("Das Mosaic Dataset wurde erfolgreich befüllt")

    # Das Feld "abgleich" wird befüllt
    with arcpy.da.UpdateCursor(mosaic_dataset, ["name", "abgleich", "operat_nr"]) as cursor:
        for row in cursor:
            if row[1] is None:
                name = row[0]
                abgleich = name + operat
                cursor.updateRow([name, abgleich, operat])


@func_info
def operate_ausserhalb_loeschen(mosaic_dataset: str, operate_ausserhalb: list):
    """
    Die Funktion löscht die Raster der Operate, die zur Gänze ausserhalb von Ö liegen.
    Parameter:
        - mosaic_dataset (str): Pfad zum Mosaic Dataset mit allen Bildern des Meridians
        - operate_ausserhalb (list): Liste von Operaten, die zur Gänze ausserhalb von Ö liegen
    """
    if len(operate_ausserhalb) >= 0:
        # Es werden alle Raster durchsucht, falls überhaupt Operate existieren die ausserhalb liegen
        with arcpy.da.UpdateCursor(mosaic_dataset, ["operat_nr"]) as cursor:
            for row in cursor:
                if row[0] in operate_ausserhalb:
                    cursor.deleteRow()
                    print("Bild wurde entfernt")
