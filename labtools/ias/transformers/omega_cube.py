"""Transformer module for OMEGA_CUBE metadata."""
from typing import Any, Dict, List, Union, Optional

from pydantic import BaseModel

from labtools.ias.schemas.omega_cube import (
    SCHEMA_NAME,
    OMEGA_Cube_Record,
    PSUP_Collection
)
from labtools.schemas.pdssp_stac import (
    PDSSP_STAC_Item,
    PDSSP_STAC_Collection,
    PDSSP_STAC_Asset,
    PDSSP_STAC_Properties
)

from labtools.schemas.pdssp_stac import (
    PDSSP_STAC_SsysProperties,
    PDSSP_STAC_ProcessingProperties,
    PDSSP_STAC_SciProperties,
)

from labtools.definitions import ItemDefinition, CollectionDefinition, CatalogDefinition
from labtools.transformers.transformer import AbstractTransformer, InvalidModelObjectTypeError
from labtools.transformers import factory as transformer_factory
from labtools.schemas import factory as metadata_factory
from labtools.utils import utc_to_iso
from labtools.ias.netcdf import get_netcdf_footprint, get_netcdf_properties

from pathlib import Path
from datetime import datetime

class OMEGA_CUBE_STAC_Transformer(AbstractTransformer):

    def get_item_id(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> str:
        return f'OMEGA_L2_{Path(metadata.download_nc).stem}'  # OMEGA_L2_ORB0018_6
        # return f'L3_{int(metadata.orbit_number):04}_{int(metadata.cube_number)}'

    def get_collection_id(self, metadata: PSUP_Collection, definition: CollectionDefinition = None) -> str:
        #assert metadata.id == definition.id
        return definition.id

    # def get_stac_version(self, metadata: BaseModel) -> str:
    #     pass

    # def get_item_links(self, metadata: BaseModel, definition: ItemDefinition = None) -> list[Link]:
    #     pass

    def get_item_assets(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> Dict[str, PDSSP_STAC_Asset]:
        item_assets = {
            'nc_data_file': PDSSP_STAC_Asset(
                href=metadata.download_nc,
                title='NetCDF4 data file',  # self.get_item_id(metadata, definition=definition),
                # description='NetCDF4 data file',
                type='application/netcdf',
                roles=['data']
            ),
            'sav_data_file': PDSSP_STAC_Asset(
                href=metadata.download_sav,
                title='IDL SAV data file',  # self.get_item_id(metadata, definition=definition),
                # description='IDL SAV data file',
                type='application/octet-stream',
                roles=['data']
            )
        }
        return item_assets

    # def get_collection_links(self, metadata: OMEGA_C_Proj_Record, definition: CollectionDefinition = None) -> list[PDSSP_STAC_Link]:
    #     return []
    #

    # def get_collection_assets(self, metadata: BaseModel, definition: CollectionDefinition = None) -> Dict[str, Asset]:
    #     pass

    # def get_stac_extensions(self, metadata: BaseModel, definition: Union[CollectionDefinition, CatalogDefinition] = None) -> list[str]:
    #     # call parent method to retrieve STAC extensions defined at collection level that are inherited by default
    #     stac_extensions = super().get_stac_extensions(metadata, definition=definition)
    #
    #     # remove 'scientific' and 'processing' extensions
    #     stac_extensions_copy = stac_extensions.copy()
    #     for stac_extension in stac_extensions:
    #         if 'scientific' in stac_extension or 'processing' in stac_extension:
    #             stac_extensions_copy.remove(stac_extension)
    #     return stac_extensions_copy

    # def get_title(self, metadata: BaseModel, definition: CollectionDefinition = None) -> str:
    #     pass

    # def get_description(self, metadata: BaseModel, definition: CollectionDefinition = None) -> str:
    #     pass

    # def get_keywords(self, metadata: BaseModel, definition: CollectionDefinition = None) -> list[str]:
    #     pass

    def get_geometry(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None, data_path: str = None) -> Optional[Dict[str, Any]]:
        """Derives and returns footprint geometry from source data file.
        """
        geometry = None
        if data_path:
            netcdf_file = Path(data_path) / 'data' / Path(metadata.download_nc).name
            if netcdf_file.exists():
                try:
                    geometry = get_netcdf_footprint(netcdf_file)
                except Exception as e:
                    print(e)
                    print(f'Unable to extract footprint geometry from source NetCDF file: {netcdf_file}')
            else:
                print(f'Source data file not found: {netcdf_file!r}')
        return geometry

    # def get_extent(self, metadata: BaseModel, definition: CollectionDefinition = None) -> Extent:
    #     pass

    def get_bbox(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> list[float]:
        return [
            (float(metadata.westernmost_longitude) + 180.0) % 360.0 - 180.0,
            float(metadata.minimum_latitude),
            (float(metadata.easternmost_longitude) + 180.0) % 360.0 - 180.0,
            float(metadata.maximum_latitude)
        ]

    # def get_providers(self, metadata: BaseModel, definition: CollectionDefinition = None) -> list[Provider]:
    #     pass

    # def get_license(self, metadata: BaseModel, definition: CollectionDefinition = None) -> str:
    #     pass

    # def get_summaries(self, metadata: BaseModel, definition: CollectionDefinition = None) -> Optional[Dict[str, Union[Range, List[Any], Dict[str, Any]]]]:
    #     pass

    def get_properties(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None, data_path: str = None) -> PDSSP_STAC_Properties:

        properties_dict = {
            'datetime': datetime.now(),
            'created': None,
            'start_datetime': None,
            'end_datetime': None,
            'mission': 'Mars Express',
            'platform': 'MEX',
            'instruments': ['OMEGA'],
            'gsd': None,
            # extra OMEGA_Cube_Record properties of interest
            'orbit_number': metadata.orbit_number,
            'cube_number': metadata.cube_number,
            'data_quality_id': metadata.data_quality_id,
            'martian_year': metadata.martian_year,
            'pointing_mode': metadata.pointing_mode,
            'l_channel_ok': metadata.l_channel_ok,
            'c_channel_ok': metadata.vis_channel_ok,
            'trimmed_orbit_number': metadata.trimmed_orbit_number,
            # PDSSP properties
            'solar_longitude': metadata.solar_longitude
        }

        # # append data file metadata if available
        if data_path:
            netcdf_file = Path(data_path) / 'data' / Path(metadata.download_nc).name
            if netcdf_file.exists():
                try:
                    netcdf_metadata_dict = get_netcdf_properties(netcdf_file, SCHEMA_NAME)
                    # print(netcdf_metadata_dict)
                    properties_dict.update(netcdf_metadata_dict)
                except Exception as e:
                    print(e)
                    print(f'Unable to extract and add properties from NetCDF file: {netcdf_file}')
            else:
                print(f'Source data file not found: {netcdf_file!r}')

        return PDSSP_STAC_Properties(**properties_dict)

    def get_ssys_properties(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> PDSSP_STAC_SsysProperties:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'item':
            ssys_properties_dict = {
                'ssys:targets': ['Mars']
            }
        else:
            raise InvalidModelObjectTypeError(object_type)

        return PDSSP_STAC_SsysProperties(**ssys_properties_dict)

    def get_ssys_fields(self, metadata: OMEGA_Cube_Record, definition: Union[ItemDefinition, CollectionDefinition] = None) -> dict:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'item':
            ssys_fields = {}
        elif object_type == 'collection':
            ssys_fields = { 'ssys:targets': definition.ssys_targets }
        else:
            raise InvalidModelObjectTypeError(object_type)
        return ssys_fields

    def get_sci_properties(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> Optional[PDSSP_STAC_SciProperties]:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'item':
            return None
        else:
            raise InvalidModelObjectTypeError(object_type)
        # return PDSSP_STAC_SciProperties(**sci_properties_dict)

    def get_sci_fields(self, metadata: OMEGA_Cube_Record, definition: Union[ItemDefinition, CollectionDefinition] = None) -> dict:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'collection':
            # set sci_publications as dict (so as to make it "serializable")
            sci_publications = []
            for sci_publication in definition.sci_publications:
                sci_publications.append(sci_publication.dict(exclude_none=True))

            sci_fields = {
                # 'sci:doi': '',
                # 'sci_citation': '',
                'sci:publications': sci_publications
            }
        elif object_type == 'item':
            sci_fields = {}
        else:
            raise InvalidModelObjectTypeError(object_type)
        return sci_fields

    def get_processing_properties(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> Optional[PDSSP_STAC_ProcessingProperties]:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'item':
            return None
        else:
            raise InvalidModelObjectTypeError(object_type)
        # return PDSSP_STAC_ProcessingProperties(**processing_properties_dict)

    def get_processing_fields(self, metadata: OMEGA_Cube_Record, definition: ItemDefinition = None) -> dict:
        object_type = metadata_factory.get_object_type(metadata)
        if object_type == 'collection':
            processing_fields = {
                'processing:level': definition.processing_level
            }
        elif object_type == 'item':
            processing_fields = {}
        else:
            raise InvalidModelObjectTypeError(object_type)
        return processing_fields

def register() -> None:
    transformer_factory.register(SCHEMA_NAME, OMEGA_CUBE_STAC_Transformer)
