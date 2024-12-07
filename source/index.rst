.. Soil_grids_downloader documentation master file, created by
   sphinx-quickstart on Wed Nov 27 00:37:35 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Soil_grids_downloader's documentation!
=================================================

The **Soil Grids Downloader** is a QGIS plugin designed to streamline the process of downloading and visualizing soil properties data. Users can extract soil attributes such as clay, sand, silt, soil organic carbon (SOC), and nitrogen content, for specific points or shapefile datasets. The plugin supports multiple functionalities including coordinate selection, property filtering, shapefile generation, and integration with external services.

Key Features:
--------------
- **Download Soil Properties**: Fetch soil data from Soil Grids API based on selected locations.
- **Point Selection**: Pick a specific point on the map to retrieve soil properties.
- **Shapefile Integration**: Add soil property fields to point shapefiles and save the updated shapefiles.
- **Clipboard Copy**: Copy soil property data for selected points directly to the clipboard.
- **Load Shapefiles**: Automatically load the generated shapefiles into the QGIS project.

.. image:: images_read_the_docs/welcome_page.png 
   :alt: Welcome page
   :align: center

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   functionality
   api_reference
   troubleshooting


Installation
============
For installation instructions, refer to the :doc:`installation` page.

Usage
=====
For details on how to use the plugin, refer to the :doc:`usage` page.

Functionality Overview
======================
The plugin provides several functionalities to streamline soil data analysis:

1. **Open Directory**: Access the plugin's working directory for shapefile management.
2. **Shapefile Selection**: Choose an existing shapefile to append soil data.
3. **Soil Properties Selection**: Specify which properties (e.g., clay, sand) to include.
4. **Map Interaction**: Select a point on the map to fetch its soil attributes.
5. **Copy to Clipboard**: Quickly copy selected data to the clipboard.
6. **Load Updated Shapefiles**: Automatically load processed shapefiles into the QGIS interface.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
