# -*- coding: utf-8 -*-
# Copyright (C) 2020-2021 - Centre National d'Etudes Spatiales
# jean-christophe.malapert@cnes.fr
#
# This file is part of planetary_fetch.
#
# planetary_fetch is a free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3.0 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301  USA
"""
Module: planetary_fetch_lib

The planetary_fetch_lib module provides a library for downloading PDS files.

Classes:
    PlanetaryFetchLib: The main library that downloads PDS files.
    PdsRequest: A class for making requests to the PDS API.
    Files: Downloads files from a list of URLs and saves them to a specified directory.
"""
import fnmatch
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from string import Template
from typing import Dict
from typing import List

import requests
from tqdm import tqdm

from ._version import __name_soft__


logger = logging.getLogger(__name__)


class NoProductFoundException(Exception):
    """No product found"""


class PlanetaryFetchLib:
    """The main library that downloads PDS files."""

    def __init__(self, directory: str, **kwargs):
        """Initialize the PlanetaryFetchLib object.

        Args:
            directory (str): The output directory for the downloaded files.
            *args: Additional arguments (not used).
            **kwargs: Keyword arguments that control the behavior of the library.
                level (str): The logging level (default: "INFO").
                max_workers (int): The maximum number of worker threads (default: 10).
        """
        PlanetaryFetchLib._parse_level(kwargs["level"])
        self.__max_workers = kwargs["max_workers"]
        self.__directory = directory
        logger.info(
            f"""Starting with:
        - level = {kwargs["level"]}
        - max workers = {kwargs["max_workers"]}
        - output directory = {directory}
        """
        )

    @staticmethod
    def _parse_level(level: str):
        """Parse level name and set the right level for the logger.
        If the level is not known, the INFO level is set

        Args:
            level (str): level name
        """
        logger_main = logging.getLogger(__name_soft__)
        if level == "INFO":
            logger_main.setLevel(logging.INFO)
        elif level == "DEBUG":
            logger_main.setLevel(logging.DEBUG)
        elif level == "WARNING":
            logger_main.setLevel(logging.WARNING)
        elif level == "ERROR":
            logger_main.setLevel(logging.ERROR)
        elif level == "CRITICAL":
            logger_main.setLevel(logging.CRITICAL)
        elif level == "TRACE":
            logger_main.setLevel(logging.TRACE)  # type: ignore # pylint: disable=no-member
        else:
            logger_main.warning(
                "Unknown level name : %s - setting level to INFO", level
            )
            logger_main.setLevel(logging.INFO)

    @property
    def max_workers(self) -> int:
        """The maximum number of worker threads.

        Returns:
            int: The maximum number of worker threads.
        """
        return self.__max_workers

    @property
    def directory(self) -> str:
        """The output directory.

        Returns:
            str: The output directory.
        """
        return self.__directory

    def _save_dict(self, metadata: Dict):
        """Save a dictionary to a file.

        Args:
            metadata (dict): The dictionary to save.
        """
        with open(
            os.path.join(self.directory, "my_dict.json"), "w"
        ) as outfile:
            # Write the dictionary to the file in JSON format
            json.dump(metadata, outfile, indent=5)

    def run(self, ids: str):
        """Download PDS files for a given set of PDS IDs.

        Args:
            ids (str): IDs to download (* is allowed).
        """
        pds_request = PdsRequest(ids)
        query = pds_request.query()
        try:
            metadata, urls = pds_request.parse_response(query)
            files = Files(urls, self.max_workers, self.directory)
            self._save_dict(metadata)
            files.download()
        except NoProductFoundException:
            logger.info("No product found")


class PdsRequest:
    """
    A class for making requests to the PDS API.

    Attributes:
    -----------
    pds_id : str
        The PDS ID of the product to query.

    Methods:
    --------
    query() -> JSON:
        Sends an HTTP GET request to the PDS API with the specified PDS ID and returns the JSON response.
    parse_response(rjson: JSON) -> Tuple[List[Dict[str, Any]], List[str]]:
        Parses the JSON response and extracts the URLs of the product files (.lbl and .img), and returns them along with
        the metadata of the products.

    """

    ODE_REQUEST_TPL = Template(
        "https://oderest.rsl.wustl.edu/live2/default.aspx?query=product&results=copmf&output=json&pdsid=$pdsid"
    )

    def __init__(self, pds_id: str):
        self.pds_id = pds_id
        self.req = PdsRequest.ODE_REQUEST_TPL.substitute(pdsid=self.pds_id)

    def query(self):
        """Sends a GET request to the PDS API and returns the JSON response."""
        response = requests.get(self.req)
        return response.json()

    def parse_response(self, rjson):
        """Extracts the metadata and file URLs from the JSON response.

        Args:
            rjson (dict): The JSON response from the PDS API.

        Returns:
            Tuple containing two lists:
            - The metadata for each product (list of dicts).
            - The URLs for each file to download (list of strings).
        """
        files = list()
        metadata = list()
        if rjson["ODEResults"]["Products"] == "No Products Found":
            raise NoProductFoundException()
        products = rjson["ODEResults"]["Products"]["Product"]
        logger.info(f"{len(products)} products found")
        for product in tqdm(products, desc="Extracting URLs"):
            metadata.append(product)
            product_files = product["Product_files"]["Product_file"]
            for product_file in product_files:
                url = product_file["URL"]
                if ".lbl" in url.lower() or ".img" in url.lower():
                    files.append(url)
        return metadata, files


class Files:
    """
    Downloads files from a list of URLs and saves them to a specified directory.

    Args:
        urls (List[str]): A list of URLs to download.
        max_workers (int): The maximum number of worker threads to use for downloading files.
        output_dir (str): The directory to save downloaded files to.

    Attributes:
        urls (List[str]): The list of URLs to download.
        output_dir (str): The directory to save downloaded files to.
        file_organizer (FileOrganizer): A FileOrganizer instance to organize downloaded files.

    Methods:
        download(): Downloads all files from the URLs list and saves them to the output directory.

    """

    def __init__(self, urls: List[str], max_workers: int, output_dir: str):
        """
        Initializes a new Files instance with the given URLs, maximum number of worker threads,
        and output directory.
        """
        self.max_workers = max_workers
        self.__urls: List[str] = urls
        self.__output_dir: str = output_dir
        self.__file_organizer = FileOrganizer(self.__output_dir)

    @property
    def urls(self) -> List[str]:
        """
        Gets the list of URLs to download.
        """
        return self.__urls

    @property
    def output_dir(self) -> str:
        """
        Gets the directory to save downloaded files to.
        """
        return self.__output_dir

    @property
    def file_organizer(self):
        """
        Gets the FileOrganizer instance used to organize downloaded files.
        """
        return self.__file_organizer

    def _download_url(self, url):
        response = requests.get(url)
        filename = url.split("/")[-1]
        self.file_organizer.filename = filename
        with open(
            os.path.join(self.file_organizer.organize(), filename), "wb"
        ) as file:
            file.write(response.content)
        return f"{filename} downloaded"

    def download(self):
        """
        Downloads all files from the URLs list and saves them to the output directory.
        """
        completed_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            completed_count = 0
            futures = []
            for url in self.urls:
                future = executor.submit(self._download_url, url)
                future.add_done_callback(
                    lambda future, count=[completed_count]: count.__setitem__(
                        0, count[0] + 1
                    )
                )
                futures.append(future)

            # Afficher une barre de progression
            with tqdm(total=len(self.urls), desc="Downloading files") as pbar:
                while len(futures) > 0:
                    for future in futures.copy():
                        if future.done():
                            futures.remove(future)
                            pbar.update(1)

                            # Mettre à jour le nombre de téléchargements terminés
                            completed_count = completed_count + 1

            # Afficher le nombre total de fichiers téléchargés
            logger.info(
                f"Total number of downloaded files : {completed_count}"
            )


class FileOrganizer:
    """
    A class used to organize downloaded files into a directory structure based on file types.

    Parameters
    ----------
    output_dir : str
        The path to the directory where downloaded files should be stored.

    Methods
    -------
    organize()
        Organizes the downloaded file by moving it to the appropriate subdirectory based on its file type.

    Attributes
    ----------
    filename : str
        The name of the file to be organized.
    """

    def __init__(self, base_directory: str):
        """Initialize the FileOrganizer.

        Args:
            base_directory (str): str
        """
        self.base_directory = base_directory
        self.__filename = None

    @property
    def filename(self) -> str:
        """Returns filename.

        Returns:
            str: filename
        """
        return self.__filename

    @filename.setter
    def filename(self, value: str):
        """Set filename

        Args:
            value (str): value
        """
        self.__filename = value

    def _build_directory_path(self, obs_type: str) -> str:
        """Define the directory based on the observation type and the filename

        Args:
            obs_type (str): _description_

        Raises:
            NotImplementedError: Not implemented use case

        Returns:
            str: the directory
        """
        logger.debug(f"try to organize {self.filename}")
        if self.filename.lower().startswith(f"{obs_type}0000"):
            subdirectory = os.path.splitext(self.filename)[0][7:9]
            subsubdirectory = os.path.splitext(self.filename)[0][7:11]
            if fnmatch.fnmatch(self.filename.lower(), "*_if*_trr3.*"):
                directory_path = os.path.join(
                    self.base_directory,
                    obs_type.upper() + subdirectory.upper(),
                    obs_type.upper() + subsubdirectory.upper(),
                    "DATA",
                )
            elif fnmatch.fnmatch(self.filename.lower(), "*_de*_ddr1.*"):
                directory_path = os.path.join(
                    self.base_directory,
                    obs_type.upper() + subdirectory.upper(),
                    obs_type.upper() + subsubdirectory.upper(),
                    "DDR",
                )
            else:
                raise NotImplementedError(
                    f"{self.filename} does not match any case"
                )
        elif self.filename.lower().startswith(f"{obs_type}000"):
            subdirectory = os.path.splitext(self.filename)[0][6:9]
            subsubdirectory = os.path.splitext(self.filename)[0][6:11]
            if fnmatch.fnmatch(self.filename.lower(), "*_if*_trr3.*"):
                directory_path = os.path.join(
                    self.base_directory,
                    obs_type.upper() + subdirectory.upper(),
                    obs_type.upper() + subsubdirectory.upper(),
                    "DATA",
                )
            elif fnmatch.fnmatch(self.filename.lower(), "*_de*_ddr1.*"):
                directory_path = os.path.join(
                    self.base_directory,
                    obs_type.upper() + subdirectory.upper(),
                    obs_type.upper() + subsubdirectory.upper(),
                    "DDR",
                )
            else:
                raise NotImplementedError(
                    f"{self.filename} does not match any case"
                )
        else:
            raise NotImplementedError(
                f"{self.filename} does not match any case"
            )

        logger.debug(f"\t -> {directory_path}")
        return directory_path

    def organize(self) -> str:
        """Create and return the path to the subdirectory where the file should be saved based on its extension.

        Returns:
            str: The path to the subdirectory where the file should be saved.
        """
        directory: str
        if self.filename.lower().startswith("frt"):
            directory = self._build_directory_path("frt")
        elif self.filename.lower().startswith("hrl"):
            directory = self._build_directory_path("hrl")
        elif self.filename.lower().startswith("hrs"):
            directory = self._build_directory_path("hrs")
        else:
            raise NotImplementedError("Only FRT, HRL and HRS are implemented")

        # Create the directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        return directory
