# -*- coding: utf-8 -*-
# Copyright (C) 2023 - Centre National d'Etudes Spatiales
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
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from string import Template
from typing import Dict
from typing import List
from urllib.parse import urlsplit

import requests
from tqdm import tqdm

from ._version import __name_soft__
from .crism import (
    CrismReport,
    find_ub_products,
    observation_directory,
    observation_id,
)

logger = logging.getLogger(__name__)

# The umask is process-wide: read it once here rather than in the download
# threads, where resetting it would briefly affect every other thread.
_UMASK = os.umask(0)
os.umask(_UMASK)


class NoProductFoundException(Exception):
    """No product found"""


class DownloadError(Exception):
    """One or more files could not be downloaded."""

    def __init__(self, failures):
        self.failures = failures
        super().__init__(
            f"{len(failures)} file(s) could not be downloaded:\n  "
            + "\n  ".join(f"{url} : {error}" for url, error in failures)
        )


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
                disable_tqdm (bool) : Disable the progress bar
        """
        PlanetaryFetchLib._parse_level(kwargs["level"])
        self.__max_workers = kwargs["max_workers"]
        self.__disable_tqdm = kwargs["disable_tqdm"]
        self.__with_ub = kwargs.get("with_ub", False)
        self.__directory = directory
        logger.info(f"""Starting with:
        - level = {kwargs["level"]}
        - max workers = {kwargs["max_workers"]}
        - output directory = {directory}
        - disable_tqdm = {kwargs["disable_tqdm"]}
        """)

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
    def disable_tqdm(self) -> bool:
        """Disable TQDM

        Returns:
            bool: True if the progress bar is disabled otherwise False
        """
        return self.__disable_tqdm

    @property
    def directory(self) -> str:
        """The output directory.

        Returns:
            str: The output directory.
        """
        return self.__directory

    def _save_dict(self, metadata: List):
        """Save a dictionary to a file.

        Args:
            metadata (dict): The dictionary to save.
        """
        file_path = os.path.join(self.directory, "my_dict.json")

        if os.path.exists(file_path):
            with open(file_path, "r") as infile:
                # Load the existing metadata from the file
                existing_metadata = json.load(infile)

            # Merge the existing metadata with the new metadata
            for item in metadata:
                if item not in existing_metadata:
                    existing_metadata.append(item)

            metadata = existing_metadata

        with open(file_path, "w") as outfile:
            # Write the merged metadata to the file in JSON format
            json.dump(metadata, outfile, indent=5)

    def run(self, ids: str):
        """Download PDS files for a given set of PDS IDs.

        Args:
            ids (str): IDs to download (* is allowed).
        """
        if self.__with_ub and not observation_id(ids):
            raise ValueError(
                "--with_ub requires a single CRISM observation ID, for example HRL000040FF*"
            )
        pds_request = PdsRequest(ids, disable_tqdm=self.disable_tqdm)
        query = pds_request.query()
        try:
            metadata, urls = pds_request.parse_response(query)
            files = Files(
                urls,
                self.max_workers,
                self.directory,
                disable_tqdm=self.disable_tqdm,
            )
            self._save_dict(metadata)
            failures = files.download()
            report = None
            obs_id = observation_id(ids)
            if obs_id:
                ub_products = []
                # The UB selection reads the TRR3 labels, which may be missing.
                if self.__with_ub and not failures:
                    ub_products = find_ub_products(
                        metadata, self.directory, obs_id
                    )
                    self._save_dict(ub_products)
                    ub_urls = [
                        file["URL"]
                        for product in ub_products
                        for file in product["Product_files"]["Product_file"]
                        if file.get("Type") == "Product"
                        and urlsplit(file["URL"])
                        .path.lower()
                        .endswith((".img", ".lbl"))
                    ]
                    failures += Files(
                        ub_urls,
                        self.max_workers,
                        self.directory,
                        disable_tqdm=self.disable_tqdm,
                        ub_observation=obs_id,
                    ).download()
                report = CrismReport(
                    metadata,
                    self.directory,
                    obs_id,
                    ub_products,
                    check_ub=self.__with_ub,
                )
                logger.info(f"\n{report.render()}")
            if failures:
                raise DownloadError(failures)
            return report
        except NoProductFoundException:
            if self.__with_ub:
                raise
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

    def __init__(self, pds_id: str, **kwargs):
        self.pds_id = pds_id
        self.req = PdsRequest.ODE_REQUEST_TPL.substitute(pdsid=self.pds_id)
        self.disable_tqdm = (
            kwargs["disable_tqdm"] if "disable_tqdm" in kwargs else False
        )

    def query(self):
        """Return all ODE products, walking the documented limit/offset pages."""
        page_size = 100
        # The manual specifies zero-based offsets. ODE has also been observed
        # to return the first product for both 0 and 1, so deduplicate pages.
        offset = 0
        products = []
        seen = set()
        merged = None
        while True:
            response = requests.get(
                self.req + f"&limit={page_size}&offset={offset}", timeout=60
            )
            response.raise_for_status()
            result = response.json()
            if merged is None:
                merged = result
            ode = result["ODEResults"]
            if ode.get("Status", "Success") != "Success":
                raise ValueError(f"ODE query failed: {ode.get('Status')}")
            page = ode.get("Products", "No Products Found")
            if page == "No Products Found" or not page:
                break
            page_products = page["Product"]
            if isinstance(page_products, dict):
                page_products = [page_products]
            new_count = 0
            for product in page_products:
                key = product.get("ode_id") or (
                    product.get("pdsid"),
                    product.get("Product_version_id"),
                )
                if key not in seen:
                    products.append(product)
                    seen.add(key)
                    new_count += 1
            if not new_count and len(page_products) == page_size:
                raise ValueError(
                    "ODE returned the same page twice; pagination did not advance"
                )
            if len(page_products) < page_size:
                break
            offset += page_size
        assert merged is not None
        merged["ODEResults"]["Count"] = str(len(products))
        merged["ODEResults"]["Products"] = (
            {"Product": products} if products else "No Products Found"
        )
        return merged

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
        for product in tqdm(
            products, desc="Extracting URLs", disable=self.disable_tqdm
        ):
            metadata.append(product)
            product_files = product["Product_files"]["Product_file"]
            if isinstance(product_files, dict):
                product_files = [product_files]
            for product_file in product_files:
                url = product_file["URL"]
                if product_file.get(
                    "Type", "Product"
                ) == "Product" and urlsplit(url).path.lower().endswith(
                    (".lbl", ".img")
                ):
                    files.append(url)
        return metadata, list(dict.fromkeys(files))


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

    def __init__(
        self, urls: List[str], max_workers: int, output_dir: str, **kwargs
    ):
        """
        Initializes a new Files instance with the given URLs, maximum number of worker threads,
        and output directory.
        """
        self.max_workers = max_workers
        self.__urls: List[str] = urls
        self.__output_dir: str = output_dir
        self.__file_organizer = FileOrganizer(self.__output_dir)
        self.__disable_tqdm = (
            kwargs["disable_tqdm"] if "disable_tqdm" in kwargs else False
        )
        self.__ub_observation = kwargs.get("ub_observation")

    def _path_for_url(self, url):
        filename = os.path.basename(urlsplit(url).path)
        if self.__ub_observation:
            obs = self.__ub_observation
            directory = os.path.join(
                observation_directory(self.output_dir, obs), "UB"
            )
            os.makedirs(directory, exist_ok=True)
        else:
            organizer = FileOrganizer(self.output_dir)
            organizer.filename = filename
            directory = organizer.organize()
        return os.path.join(directory, filename)

    @property
    def urls(self) -> List[str]:
        """
        Gets the list of URLs to download.
        """
        return self.__urls

    @property
    def disable_tqdm(self) -> bool:
        """
        Get the disable_tqdm
        """
        return self.__disable_tqdm

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
        logger.debug(f"Downloading {url} ...")
        filepath = self._path_for_url(url)
        filename = os.path.basename(filepath)
        try:
            if os.path.exists(filepath):
                logger.debug(
                    f"\t{filename} is already complete, skip the download"
                )
            else:
                temp_path = None
                try:
                    with requests.get(
                        url, stream=True, timeout=60
                    ) as response:
                        response.raise_for_status()
                        with tempfile.NamedTemporaryFile(
                            dir=os.path.dirname(filepath), delete=False
                        ) as file:
                            temp_path = file.name
                            for chunk in response.iter_content(
                                chunk_size=1024 * 1024
                            ):
                                if chunk:
                                    file.write(chunk)
                    os.chmod(temp_path, 0o666 & ~_UMASK)
                    os.replace(temp_path, filepath)
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                logger.debug(f"\t{filename} downloaded")
            return
        except NotImplementedError as err:
            logger.warning(f"\tSkip the download of {url} : {err}")
            return

    def _url_to_download(self) -> List[str]:
        """URL to download based on the current URL already downloaded

        Returns:
            List[str]: List of URL to download
        """
        list_to_download = list()
        skipped_count = 0
        for url in self.urls:
            filename = os.path.basename(urlsplit(url).path)
            try:
                filepath = self._path_for_url(url)
                if os.path.exists(filepath):
                    logger.debug(
                        f"\t{filename} is already downloaded, skip the download"
                    )
                else:
                    list_to_download.append(url)

            except NotImplementedError as err:
                skipped_count += 1
                logger.debug(f"\tSkip the download of {url} : {err}")

        if skipped_count:
            logger.warning(
                f"{skipped_count} file(s) skipped: no storage rule "
                "(use --level DEBUG to list them)"
            )
        logger.info(f"{len(list_to_download)} file(s) to download")
        return list_to_download

    def download(self):
        """
        Downloads all files from the URLs list and saves them to the output directory.

        A failed file does not stop the other downloads.

        Returns:
            List[Tuple[str, Exception]]: the URLs that failed, with their error
        """
        completed_count = 0
        failures = []

        # Get the URLs to download based on the current URLs already downloaded
        list_to_download: List[str] = self._url_to_download()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_url, url): url
                for url in list_to_download
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Downloading file(s)",
                disable=self.disable_tqdm,
            ):
                error = future.exception()
                if error is None:
                    completed_count += 1
                else:
                    logger.error(f"\tFailed to download {futures[future]} : {error}")
                    failures.append((futures[future], error))

        # Afficher le nombre total de fichiers téléchargés
        logger.info(f"Total number of downloaded file(s) : {completed_count}")
        if failures:
            logger.error(f"Number of failed download(s) : {len(failures)}")
        return failures


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
        """Define the directory based on the observation type and filename."""
        stem = os.path.splitext(self.filename)[0]
        obs_id = stem.split("_", 1)[0].upper()

        if not obs_id.lower().startswith(obs_type):
            raise NotImplementedError(
                f"{self.filename} does not match observation type {obs_type}"
            )

        base_directory = observation_directory(self.base_directory, obs_id)

        if fnmatch.fnmatch(self.filename.lower(), "*_if*_trr3.*"):
            directory_path = os.path.join(base_directory, "DATA")
        elif fnmatch.fnmatch(self.filename.lower(), "*_de*_ddr1.*"):
            directory_path = os.path.join(base_directory, "DDR")
        else:
            raise NotImplementedError(
                f"{self.filename} does not match any case for storage"
            )

        logger.debug(f"\t {self.filename} -> {directory_path}")
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
