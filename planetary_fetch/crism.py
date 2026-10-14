"""CRISM observation checks and selection of referenced UB calibration products."""

import os
import re

OBSERVATION = re.compile(r"^(?:FRT|HRL|HRS)[0-9A-F]{8}", re.I)
UB_ID = re.compile(
    r"CDR4(?P<partition>\d)(?P<seconds>\d{10})_UB(?P<code>\d{7})(?P<channel>[SL])_[0-9A-Z]",
    re.I,
)
SCIENCE_ID = re.compile(
    r"_(?P<view>[0-9A-F]{2})_(?P<kind>IF|DE|SC)\d+(?P<channel>[SL])_(?P<level>TRR3|DDR1|EDR0)$",
    re.I,
)


def observation_id(ids):
    """Return a CRISM targeted observation ID for a query such as HRL000040FF*."""
    match = OBSERVATION.match(ids)
    if not match:
        return None
    obs_id = match.group().upper()
    return obs_id if ids.upper() in (obs_id, obs_id + "*") else None


def observation_directory(root, obs_id):
    if obs_id[3:7] == "0000":
        start, group_length, observation_length = 7, 2, 4
    else:
        start, group_length, observation_length = 6, 3, 5

    return os.path.join(
        root,
        obs_id[:3] + obs_id[start : start + group_length],
        obs_id[:3] + obs_id[start : start + observation_length],
    )


def _sclk(value):
    match = re.search(r"(\d+)/(\d+)", str(value))
    if not match:
        raise ValueError(f"Invalid spacecraft clock count: {value!r}")
    return int(match.group(1)), int(match.group(2))


def _reference_product(metadata, obs_id, channel):
    candidates = []
    for product in metadata:
        pdsid = product.get("pdsid", "").upper()
        if not pdsid.startswith(obs_id + "_"):
            continue
        match = SCIENCE_ID.search(pdsid)
        if (
            match
            and match.group("kind") == "IF"
            and match.group("level") == "TRR3"
            and match.group("channel") == channel
        ):
            candidates.append(
                (match.group("view") != "07", match.group("view"), product)
            )
    if not candidates:
        raise ValueError(f"No IF/TRR3 {channel} product for {obs_id}")
    return min(candidates, key=lambda item: item[:2])[2]


def _choose_ub(product, label_path, channel):
    with open(label_path, encoding="latin-1") as label:
        content = label.read()
    reference = product.get("SpaceCraft_clock_start_count")
    if not reference:
        clock_match = re.search(
            r"SPACECRAFT_CLOCK_START_COUNT\s*=\s*\"([^\"]+)\"", content
        )
        reference = clock_match.group(1) if clock_match else None
    partition, seconds = _sclk(reference)
    source_block = re.search(
        r"SOURCE_PRODUCT_ID\s*=\s*\{([^}]*)\}", content, re.S
    )
    if not source_block:
        raise ValueError(f"No SOURCE_PRODUCT_ID list in {label_path}")
    source_ids = {
        match.group().upper(): match
        for match in UB_ID.finditer(source_block.group(1))
        if match.group("channel").upper() == channel
    }
    frame_rate = re.search(r"MRO:FRAME_RATE\s*=\s*([\d.]+)", content)
    binning = re.search(r"PIXEL_AVERAGING_WIDTH\s*=\s*(\d+)", content)
    exposure = re.search(r"MRO:EXPOSURE_PARAMETER\s*=\s*(\d+)", content)
    wavelength = re.search(r'MRO:WAVELENGTH_FILTER\s*=\s*"?(\d+)"?', content)
    # CDR4 f/b/eee/w fields: CRISM Data Product SIS, linked in README.
    frame_codes = {1.0: "0", 3.75: "1", 156.0: "3", 30.0: "4"}
    bin_codes = {1: "0", 2: "1", 5: "2", 10: "3"}
    expected_code = None
    if all((frame_rate, binning, exposure, wavelength)):
        frame_code = frame_codes.get(float(frame_rate.group(1)))
        bin_code = bin_codes.get(int(binning.group(1)))
        if frame_code and bin_code:
            expected_code = (
                f"{frame_code}{bin_code}{int(exposure.group(1)):03d}"
                f"{wavelength.group(1)}"
            )
    options = [
        (
            abs(int(match.group("seconds")) - seconds),
            int(match.group("seconds")),
            pdsid,
        )
        for pdsid, match in source_ids.items()
        if int(match.group("partition")) == partition
        and (
            expected_code is None
            or match.group("code").startswith(expected_code)
        )
    ]
    if not options:
        raise ValueError(
            f"No compatible referenced UB {channel} with SCLK partition {partition} in {label_path}"
        )
    return min(options)[2]


def find_ub_products(metadata, directory, obs_id):
    """Find the closest source UB for S and L using the view 07 TRR3 labels."""
    # Local import avoids a cycle with the generic ODE request class.
    from .planetary_fetch import PdsRequest

    selected = []
    data_dir = os.path.join(observation_directory(directory, obs_id), "DATA")
    for channel in ("S", "L"):
        product = _reference_product(metadata, obs_id, channel)
        label = os.path.join(data_dir, product["pdsid"].lower() + ".lbl")
        if not os.path.isfile(label):
            raise FileNotFoundError(
                f"TRR3 label required to select UB: {label}"
            )
        ub_id = _choose_ub(product, label, channel)
        result = PdsRequest(ub_id).query()["ODEResults"]["Products"]
        if result == "No Products Found":
            raise ValueError(f"ODE has no referenced UB product {ub_id}")
        products = result["Product"]
        if len(products) != 1 or products[0].get("pdsid", "").upper() != ub_id:
            raise ValueError(
                f"ODE returned an ambiguous UB result for {ub_id}"
            )
        selected.append(products[0])
    return selected


class CrismReport:
    """Check downloaded IMG/LBL pairs for each observed CRISM view and UB channel."""

    def __init__(
        self, metadata, directory, obs_id, ub_products=(), check_ub=False
    ):
        self.obs_id = obs_id
        self.directory = observation_directory(directory, obs_id)
        self.ub_products = ub_products
        self.check_ub = check_ub
        self.views = set()
        for product in metadata:
            pdsid = product.get("pdsid", "").upper()
            if pdsid.startswith(obs_id + "_"):
                match = SCIENCE_ID.search(pdsid)
                if match and match.group("view") != "00":
                    self.views.add(match.group("view"))
        for folder in ("DATA", "DDR"):
            path = os.path.join(self.directory, folder)
            if os.path.isdir(path):
                for filename in os.listdir(path):
                    match = SCIENCE_ID.search(
                        os.path.splitext(filename)[0].upper()
                    )
                    if match and match.group("view") != "00":
                        self.views.add(match.group("view"))

    def _complete(self, folder, view, channel):
        path = os.path.join(self.directory, folder)
        if not os.path.isdir(path):
            return False
        kind, level = ("IF", "TRR3") if folder == "DATA" else ("DE", "DDR1")
        stems = set()
        for filename in os.listdir(path):
            stem, ext = os.path.splitext(filename.lower())
            match = SCIENCE_ID.search(stem.upper())
            if (
                match
                and match.group("view") == view
                and match.group("kind") == kind
                and match.group("level") == level
                and match.group("channel") == channel
                and ext in (".img", ".lbl")
            ):
                stems.add(stem)
        return any(
            all(
                os.path.isfile(os.path.join(path, stem + ext))
                for ext in (".img", ".lbl")
            )
            for stem in stems
        )

    def _ub_complete(self, channel):
        path = os.path.join(self.directory, "UB")
        for product in self.ub_products:
            pdsid = product.get("pdsid", "")
            match = UB_ID.fullmatch(pdsid)
            if match and match.group("channel").upper() == channel:
                return all(
                    os.path.isfile(os.path.join(path, pdsid.lower() + ext))
                    for ext in (".img", ".lbl")
                )
        return False

    @property
    def complete(self):
        return (
            bool(self.views)
            and all(
                self._complete(folder, view, channel)
                for view in self.views
                for folder in ("DATA", "DDR")
                for channel in ("S", "L")
            )
            and (
                not self.check_ub
                or all(self._ub_complete(c) for c in ("S", "L"))
            )
        )

    def render(self):
        lines = [
            f"Observation {self.obs_id}",
            "VIEW  DATA-S  DATA-L  DDR-S  DDR-L",
        ]
        missing = []
        for view in sorted(self.views):
            cells = []
            for folder, channel in (
                ("DATA", "S"),
                ("DATA", "L"),
                ("DDR", "S"),
                ("DDR", "L"),
            ):
                ok = self._complete(folder, view, channel)
                cells.append("OK" if ok else "MISSING")
                if not ok:
                    missing.append(
                        f"{folder} view {view} channel {channel} IMG/LBL pair"
                    )
            lines.append(
                f"{view:>4}  " + "  ".join(f"{cell:>7}" for cell in cells)
            )
        if not self.views:
            missing.append("No CRISM science views found")
        if self.check_ub:
            for channel in ("S", "L"):
                if not self._ub_complete(channel):
                    missing.append(f"UB channel {channel} IMG/LBL pair")
            lines.append(
                "UB: "
                + (
                    "complete"
                    if all(self._ub_complete(c) for c in ("S", "L"))
                    else "incomplete"
                )
            )
        lines.append(
            "STATUS: " + ("COMPLETE" if not missing else "INCOMPLETE")
        )
        if missing:
            lines.append("Missing:\n  " + "\n  ".join(missing))
        return "\n".join(lines)
