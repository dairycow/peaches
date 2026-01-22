"""IB Gateway scanner extension."""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from ibapi.common import TagValue
from ibapi.scanner import ScannerSubscription
from loguru import logger

from app.scanner.models import GapCandidate

if TYPE_CHECKING:
    pass


class IBScanner:
    """Wrapper for IB scanner functionality."""

    def __init__(self) -> None:
        """Initialize IB scanner."""
        self._scanner_results: list[GapCandidate] = []
        self._scanner_callbacks: dict[int, dict[str, Literal["up", "down"]]] = {}

    def request_gap_scan(
        self,
        req_id: int,
        scan_direction: Literal["up", "down"],
        filters: list[TagValue] | None = None,
    ) -> None:
        """Request gap scan from IB.

        Args:
            req_id: Request ID
            scan_direction: "up" or "down"
            filters: Optional list of filter parameters
        """
        scanner = ScannerSubscription()

        scanner.instrument = "STK"
        scanner.locationCode = "STK.AU"
        scanner.numberOfRows = 50

        if scan_direction == "up":
            scanner.scanCode = "TOP_CLOSE_TO_OPEN_PERC_GAIN"
        elif scan_direction == "down":
            scanner.scanCode = "TOP_CLOSE_TO_OPEN_PERC_LOSER"
        else:
            raise ValueError(f"Invalid scan direction: {scan_direction}")

        scanner.scanSettingPairs = ""

        if filters:
            scanner.scanSettingPairs = ",".join(f"{f.tag}={f.value}" for f in filters)

        logger.info(
            f"Requesting {scan_direction} gap scan (req_id={req_id}): "
            f"{scanner.scanCode}, location={scanner.locationCode}"
        )

        self._scanner_results = []
        self._scanner_callbacks[req_id] = {"direction": scan_direction}

    def cancel_scan(self, req_id: int) -> None:
        """Cancel active scanner scan.

        Args:
            req_id: Request ID
        """
        self._scanner_callbacks.pop(req_id, None)
        logger.info(f"Cancelled scanner request {req_id}")

    def scannerDataCallback(  # noqa: N802
        self,
        req_id: int,
        rank: int,
        contract_details,
        distance,
        benchmark,
        projection,  # noqa: ARG002
        legsStr,  # noqa: ARG002,N803
    ) -> None:
        """Handle scanner data callback.

        Args:
            req_id: Request ID
            rank: Rank in scan results
            contract_details: Contract details object
            distance: Distance from benchmark
            benchmark: Benchmark value
            projection: Projection type
            legsStr: Legs string
        """
        if req_id in self._scanner_callbacks:
            direction = self._scanner_callbacks[req_id]["direction"]

            gap_candidate = GapCandidate(
                symbol=contract_details.contract.symbol,
                gap_percent=0.0,
                gap_direction=direction,
                previous_close=0.0,
                open_price=0.0,
                volume=0,
                price=0.0,
                timestamp=datetime.min,
                conid=contract_details.contract.conId,
            )

            self._scanner_results.append(gap_candidate)

            logger.debug(
                f"Scanner result {req_id}: {gap_candidate.symbol} "
                f"(rank={rank}, gap={distance}, benchmark={benchmark})"
            )

    def scannerDataEndCallback(  # noqa: N802
        self, req_id: int
    ) -> None:
        """Handle scanner data end callback.

        Args:
            req_id: Request ID
        """
        if req_id in self._scanner_callbacks:
            direction = self._scanner_callbacks[req_id]["direction"]
            logger.info(
                f"Scanner scan {req_id} complete: {direction} gap scan "
                f"completed with {len(self._scanner_results)} results"
            )
        else:
            logger.info(f"Scanner scan {req_id} complete")

    def get_results(self) -> list[GapCandidate]:
        """Get scanner results.

        Returns:
            List of gap candidates
        """
        return self._scanner_results

    def clear_results(self) -> None:
        """Clear scanner results."""
        self._scanner_results = []
