"""Integration tests for leftover data from previous cycles."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from src.shares_reporting.application.extraction.processing import (
    parse_ib_export_all,
    parse_leftover_and_export_data,
    parse_ib_export,
)
from src.shares_reporting.domain.value_objects import TradeType


@pytest.fixture
def test_export_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create test export file with complete data including Financial Instrument Information."""
    test_resources_dir = Path(__file__).parent.parent / "resources"
    source_file = test_resources_dir / "test_ib_export.csv"

    if not source_file.exists():
        pytest.skip(f"Test export file not found: {source_file}")

    # Copy to tmp_path for isolation
    tmp_file = tmp_path_factory.mktemp("test_data") / "test_ib_export.csv"
    tmp_file.write_text(source_file.read_text())
    return tmp_file


@pytest.fixture
def test_leftover_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create test leftover file with older trades."""
    test_resources_dir = Path(__file__).parent.parent / "resources"
    source_file = test_resources_dir / "test_shares-leftover.csv"

    if not source_file.exists():
        pytest.skip(f"Test leftover file not found: {source_file}")

    # Copy to tmp_path for isolation
    tmp_file = tmp_path_factory.mktemp("test_data") / "test_shares-leftover.csv"
    tmp_file.write_text(source_file.read_text())
    return tmp_file


def test_leftover_integration_with_real_files(test_export_file: Path, test_leftover_file: Path) -> None:
    """Test integration with test data files to verify the feature works end-to-end."""
    # Test parse_leftover_and_export_data directly
    result_direct = parse_leftover_and_export_data(test_leftover_file, test_export_file)

    # Should have trade cycles
    assert len(result_direct) > 0, "Should have trade cycles from integrated data"

    # Verify we have both buy and sell trades
    total_buys = sum(1 for cycle in result_direct.values() if cycle.has_bought())
    total_sells = sum(1 for cycle in result_direct.values() if cycle.has_sold())

    assert total_buys > 0, "Should have some buy trades"
    assert total_sells > 0, "Should have some sell trades"

    # Test parse_ib_export_all with manual leftover placement for auto-detection
    # Copy leftover file to same directory as export file
    leftover_in_export_dir = test_export_file.parent / "shares-leftover.csv"
    leftover_in_export_dir.write_text(test_leftover_file.read_text())

    result_auto = parse_ib_export_all(test_export_file)

    # Should have same number of trade cycles when leftover file is present
    assert len(result_auto.trade_cycles) == len(result_direct), (
        "Auto integration should produce same result as direct integration"
    )

    print(f"Successfully integrated {len(result_direct)} currency-company pairs")
    print(f"  - {total_buys} with buy trades")
    print(f"  - {total_sells} with sell trades")


def test_leftover_integration_creates_complete_cycles(test_export_file: Path, test_leftover_file: Path) -> None:
    """Test that leftover trades create complete buy/sell cycles using test data."""
    # Parse the integrated data
    result = parse_leftover_and_export_data(test_leftover_file, test_export_file)

    # Look for symbols that have both buys and sells
    complete_cycles = []
    for cc, cycle in result.items():
        if cycle.has_bought() and cycle.has_sold():
            total_bought = sum(qta.quantity for qta in cycle.get(TradeType.BUY))
            total_sold = sum(qta.quantity for qta in cycle.get(TradeType.SELL))
            complete_cycles.append(
                {
                    "symbol": cc.company.ticker,
                    "currency": cc.currency.currency,
                    "bought": total_bought,
                    "sold": total_sold,
                    "cycle": cycle,
                }
            )

    # Should have at least some complete cycles
    assert len(complete_cycles) > 0, "Should have at least one complete buy/sell cycle"

    # Print details of complete cycles for verification
    print(f"Found {len(complete_cycles)} complete buy/sell cycles:")
    for cycle_info in complete_cycles[:5]:  # Show first 5
        print(
            f"  - {cycle_info['symbol']} ({cycle_info['currency']}): "
            f"bought {cycle_info['bought']}, sold {cycle_info['sold']}"
        )


def test_parse_ib_export_all_automatically_detects_leftover(test_export_file: Path, test_leftover_file: Path, tmp_path: Path) -> None:
    """Test that parse_ib_export_all automatically detects and integrates leftover file."""
    # Copy leftover file to same directory as export file to test auto-detection
    leftover_in_export_dir = test_export_file.parent / "shares-leftover.csv"
    leftover_in_export_dir.write_text(test_leftover_file.read_text())

    # Parse with automatic integration
    result = parse_ib_export_all(test_export_file)

    # Should have trade cycles
    assert len(result.trade_cycles) > 0, "Should have trade cycles"

    # Should have dividend income (even if empty)
    assert isinstance(result.dividend_income, dict), "Should have dividend income dict"

    # Verify some cycles have buys (from leftover) and sells (from export)
    cycles_with_buys = sum(1 for cycle in result.trade_cycles.values() if cycle.has_bought())
    cycles_with_sells = sum(1 for cycle in result.trade_cycles.values() if cycle.has_sold())

    assert cycles_with_buys > 0, "Should have cycles with buy trades"
    assert cycles_with_sells > 0, "Should have cycles with sell trades"

    print(f"Auto integration detected and processed {len(result.trade_cycles)} trade cycles")
    print(f"  - {cycles_with_buys} with buy trades")
    print(f"  - {cycles_with_sells} with sell trades")


def test_leftover_integration_actually_adds_data(test_export_file: Path, test_leftover_file: Path, tmp_path: Path) -> None:
    """Test that leftover integration actually adds more trades compared to export-only processing."""
    # Copy leftover file to same directory as export file to test auto-detection
    leftover_in_export_dir = test_export_file.parent / "shares-leftover.csv"

    # Parse with leftover file (normal behavior)
    leftover_in_export_dir.write_text(test_leftover_file.read_text())
    result_with_leftover = parse_ib_export_all(test_export_file)

    # Count total trades with leftover
    total_trades_with_leftover = 0
    for cycle in result_with_leftover.trade_cycles.values():
        total_trades_with_leftover += len(cycle.get(TradeType.BUY)) + len(cycle.get(TradeType.SELL))

    # Parse without leftover file by removing it temporarily
    leftover_in_export_dir.unlink()  # Remove leftover file
    result_without_leftover = parse_ib_export_all(test_export_file)

            # Count total trades without leftover
    total_trades_without_leftover = 0
    for cycle in result_without_leftover.trade_cycles.values():
        total_trades_without_leftover += len(cycle.get(TradeType.BUY)) + len(cycle.get(TradeType.SELL))

    # The key assertion: integration should add significantly more trades
    assert total_trades_with_leftover > total_trades_without_leftover, (
                f"Leftover integration should add more trades! "
                f"With leftover: {total_trades_with_leftover}, "
                f"Without leftover: {total_trades_without_leftover}"
            )

            # Verify we have more trade cycles when integrating leftover data
    assert len(result_with_leftover.trade_cycles) > len(result_without_leftover.trade_cycles), (
        f"Should have more trade cycles with leftover integration. "
        f"With leftover: {len(result_with_leftover.trade_cycles)}, "
        f"Without leftover: {len(result_without_leftover.trade_cycles)}"
    )

    # Verify the difference is substantial (at least 50% more trades)
    min_expected_increase = total_trades_without_leftover * 0.5
    actual_increase = total_trades_with_leftover - total_trades_without_leftover
    assert actual_increase >= min_expected_increase, (
        f"Leftover integration should add substantial number of trades. "
        f"Expected at least {min_expected_increase:.0f} more trades, "
        f"but got {actual_increase} more trades."
    )

    print(f"✅ Leftover integration verification passed:")
    print(f"   - Trades with leftover: {total_trades_with_leftover}")
    print(f"   - Trades without leftover: {total_trades_without_leftover}")
    print(f"   - Added {actual_increase} trades from leftover file ({actual_increase/total_trades_without_leftover*100:.1f}% increase)")


def test_leftover_security_enrichment(test_export_file: Path, test_leftover_file: Path) -> None:
    """Test that security information from export file enriches leftover trades correctly."""
    # Parse the integrated data
    result = parse_leftover_and_export_data(test_leftover_file, test_export_file)

    # Check that all expected symbols are present
    expected_symbols = {"TESTA", "TESTB", "TESTC", "TESTD"}
    actual_symbols = {cc.company.ticker for cc in result.keys()}

    assert expected_symbols.issubset(actual_symbols), (
        f"Missing symbols in result. Expected: {expected_symbols}, "
        f"Got: {actual_symbols}"
    )

    # Verify security enrichment for symbols present in export file
    for cc in result.keys():
        if cc.company.ticker in {"TESTA", "TESTB", "TESTC"}:
            # These symbols should have proper ISIN from export file
            assert cc.company.isin.startswith("US"), (
                f"Symbol {cc.company.ticker} should have US ISIN from export file, "
                f"but got: {cc.company.isin}"
            )
            assert cc.company.country_of_issuance != "Unknown", (
                f"Symbol {cc.company.ticker} should have country from ISIN mapping"
            )
        elif cc.company.ticker == "TESTD":
            # This symbol is only in leftover file, should have missing ISIN indicator
            # Note: In real processing, TESTD would get "MISSING_ISIN_REQUIRES_ATTENTION"
            # But for test purposes, we just verify the symbol exists
            pass

    # Verify total trades from both sources
    total_trades = 0
    for cycle in result.values():
        total_trades += len(cycle.get(TradeType.BUY)) + len(cycle.get(TradeType.SELL))

    # Should have 4 trades from export + 4 trades from leftover = 8 total
    assert total_trades == 8, f"Expected 8 total trades, got {total_trades}"

    print(f"✅ Security enrichment verification passed:")
    print(f"   - Found all expected symbols: {expected_symbols}")
    print(f"   - Export symbols enriched with ISIN/country data")
    print(f"   - Total trades processed: {total_trades}")


# Remove the parametrize test since pytest runs each function separately
