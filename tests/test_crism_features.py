"""Regression tests for ODE pagination and CRISM product selection."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from planetary_fetch.crism import (
    CrismReport,
    _choose_ub,
    observation_directory,
)
from planetary_fetch.planetary_fetch import Files, PdsRequest


def ode_page(products):
    return {
        "ODEResults": {
            "Status": "Success",
            "Products": (
                {"Product": products} if products else "No Products Found"
            ),
        }
    }


class PaginationTests(unittest.TestCase):
    def test_collects_all_pages_and_deduplicates_overlap(self):
        first = [
            {
                "ode_id": str(i),
                "pdsid": f"HRL{i}",
                "Product_files": {"Product_file": []},
            }
            for i in range(100)
        ]
        second = [
            first[-1],
            {
                "ode_id": "100",
                "pdsid": "HRL100",
                "Product_files": {"Product_file": []},
            },
        ]
        with patch("planetary_fetch.planetary_fetch.requests.get") as get:
            get.side_effect = [
                Mock(**{"json.return_value": ode_page(first)}),
                Mock(**{"json.return_value": ode_page(second)}),
            ]
            response = PdsRequest("HRL*").query()
        self.assertEqual(
            len(response["ODEResults"]["Products"]["Product"]), 101
        )
        self.assertEqual(response["ODEResults"]["Count"], "101")
        self.assertEqual(response["ODEResults"]["Status"], "Success")
        self.assertIn("offset=0", get.call_args_list[0].args[0])
        self.assertIn("offset=100", get.call_args_list[1].args[0])
        self.assertEqual(
            response["ODEResults"]["Products"]["Product"][0]["pdsid"],
            "HRL0",
        )

    def test_single_product_and_file_urls(self):
        product = {
            "ode_id": "1",
            "pdsid": "X",
            "Product_files": {
                "Product_file": {
                    "URL": "https://example.org/test.img",
                    "Type": "Product",
                }
            },
        }
        with patch("planetary_fetch.planetary_fetch.requests.get") as get:
            get.return_value = Mock(**{"json.return_value": ode_page(product)})
            request = PdsRequest("X")
            metadata, urls = request.parse_response(request.query())
        self.assertEqual(len(metadata), 1)
        self.assertEqual(urls, ["https://example.org/test.img"])

    def test_repeated_full_page_raises(self):
        products = [{"ode_id": str(i)} for i in range(100)]
        with patch("planetary_fetch.planetary_fetch.requests.get") as get:
            get.return_value = Mock(
                **{"json.return_value": ode_page(products)}
            )
            with self.assertRaisesRegex(
                ValueError, "pagination did not advance"
            ):
                PdsRequest("X*").query()


class CrismTests(unittest.TestCase):
    def test_ub_uses_references_to_break_sclk_tie(self):
        label = (
            'SOURCE_PRODUCT_ID = {"CDR420854534903_UB1118400S_3", '
            '"CDR420854534903_UB1318400S_3", '
            '"CDR420854535041_UB1118400S_3"}\n'
            "MRO:FRAME_RATE = 3.75 <HZ>\n"
            "PIXEL_AVERAGING_WIDTH = 10\n"
            "MRO:EXPOSURE_PARAMETER = 184\n"
            'MRO:WAVELENGTH_FILTER = "0"\n'
        )
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "test.lbl")
            with open(path, "w") as stream:
                stream.write(label)
            product = {"SpaceCraft_clock_start_count": "2/0854534909:03470"}
            self.assertEqual(
                _choose_ub(product, path, "S"), "CDR420854534903_UB1318400S_3"
            )

    def test_report_marks_missing_pair_and_ub(self):
        obs = "HRL000040FF"
        with tempfile.TemporaryDirectory() as root:
            data = os.path.join(observation_directory(root, obs), "DATA")
            ddr = os.path.join(observation_directory(root, obs), "DDR")
            os.makedirs(data)
            os.makedirs(ddr)
            metadata = []
            for view in ("01", "0B"):
                for channel in ("S", "L"):
                    metadata.append(
                        {"pdsid": f"{obs}_{view}_SC156{channel}_EDR0"}
                    )
                    for folder, kind, level in (
                        (data, "IF", "TRR3"),
                        (ddr, "DE", "DDR1"),
                    ):
                        if view == "0B" and channel == "L" and folder == data:
                            continue
                        for extension in ("img", "lbl"):
                            name = f"{obs}_{view}_{kind}156{channel}_{level}.{extension}".lower()
                            open(os.path.join(folder, name), "wb").close()
            report = CrismReport(metadata, root, obs, check_ub=True)
            self.assertFalse(report.complete)
            self.assertIn("DATA view 0B channel L", report.render())
            self.assertIn("UB channel S", report.render())

    def test_ub_directory_is_observation_specific(self):
        with tempfile.TemporaryDirectory() as root:
            url = "https://example.org/cdr420854534903_ub1118400s_3.img"
            files = Files(
                [url], 1, root, ub_observation="HRL000040FF", disable_tqdm=True
            )
            path = files._path_for_url(url)
            self.assertIn(os.path.join("HRL40", "HRL40FF", "UB"), path)

    def test_downloads_are_placed_in_their_own_directories(self):
        urls = [
            "https://example.org/hrl000040ff_01_if156s_trr3.img",
            "https://example.org/hrl000040ff_01_de156s_ddr1.img",
        ]

        def response_for(url, **_):
            response = MagicMock()
            response.__enter__.return_value = response
            response.iter_content.return_value = [url.encode()]
            return response

        with tempfile.TemporaryDirectory() as root:
            with patch(
                "planetary_fetch.planetary_fetch.requests.get",
                side_effect=response_for,
            ):
                Files(urls, 2, root, disable_tqdm=True).download()
            for folder, url in zip(("DATA", "DDR"), urls):
                path = os.path.join(
                    observation_directory(root, "HRL000040FF"),
                    folder,
                    url.rsplit("/", 1)[-1],
                )
                with open(path, "rb") as stream:
                    self.assertEqual(stream.read(), url.encode())

    def test_cli_returns_nonzero_for_incomplete_observation(self):
        from planetary_fetch import __main__

        options = SimpleNamespace(
            ids="HRL000040FF*",
            output_dir="/tmp",
            level="INFO",
            max_workers=1,
            disable_tqdm=True,
            with_ub=False,
        )
        with patch.object(__main__, "parse_cli", return_value=options):
            with patch.object(__main__, "PlanetaryFetchLib") as fetch:
                fetch.return_value.run.return_value.complete = False
                with self.assertRaises(SystemExit) as exit_error:
                    __main__.run()
        self.assertEqual(exit_error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
