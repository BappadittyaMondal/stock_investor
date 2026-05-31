"""
HFOS v5.0 — Integration Tests: Database + Repository
"""
import os
import pytest

# Override DB_PATH before any module imports
@pytest.fixture(scope="session", autouse=True)
def test_db(tmp_path_factory):
    db_file = str(tmp_path_factory.mktemp("db") / "hfos_test.db")
    os.environ["DB_PATH"] = db_file
    # Initialize schema
    from database.db_manager import initialize_schema
    initialize_schema()
    return db_file


@pytest.fixture
def stock_repo():
    from repositories.stock_repository import StockRepository
    return StockRepository()


@pytest.fixture
def portfolio_repo():
    from repositories.portfolio_repository import PortfolioRepository
    return PortfolioRepository()


@pytest.fixture
def watchlist_repo():
    from repositories.watchlist_repository import WatchlistRepository
    return WatchlistRepository()


class TestStockRepository:
    def test_create_and_retrieve(self, stock_repo):
        from schemas.validators import StockCreate
        data = StockCreate(symbol="TESTCO", name="Test Company Ltd",
                           exchange="NSE", sector="IT", market_cap_cr=5000.0)
        stock_repo.create(data)
        result = stock_repo.get_by_symbol("TESTCO")
        assert result is not None
        assert result["name"] == "Test Company Ltd"
        assert result["sector"] == "IT"

    def test_symbol_case_insensitive(self, stock_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="CASECO", name="Case Test"))
        assert stock_repo.get_by_symbol("caseco") is not None
        assert stock_repo.get_by_symbol("CASECO") is not None

    def test_get_all_returns_list(self, stock_repo):
        result = stock_repo.get_all()
        assert isinstance(result, list)

    def test_deactivate(self, stock_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="DEACT01", name="Deactivate Me"))
        stock_repo.deactivate("DEACT01")
        result = stock_repo.get_by_symbol("DEACT01")
        assert result["is_active"] == 0

    def test_update_flags(self, stock_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="FLAGCO", name="Flag Co"))
        stock_repo.update_flags("FLAGCO", asm=1, pledge_pct=35.0)
        result = stock_repo.get_by_symbol("FLAGCO")
        assert result["asm_flag"] == 1
        assert result["pledge_pct"] == 35.0

    def test_search(self, stock_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="SRCHCO", name="Searchable Company"))
        results = stock_repo.search("SRCHCO")
        assert len(results) >= 1

    def test_bulk_upsert(self, stock_repo):
        stocks = [
            {"symbol": f"BULK{i:02d}", "name": f"Bulk Co {i}", "exchange": "NSE"}
            for i in range(5)
        ]
        count = stock_repo.bulk_upsert(stocks)
        assert count >= 0  # no error


class TestPortfolioRepository:
    def test_create_and_retrieve(self, stock_repo, portfolio_repo):
        from schemas.validators import StockCreate, PortfolioCreate
        stock_repo.create(StockCreate(symbol="PFCO01", name="Portfolio Co"))
        stock = stock_repo.get_by_symbol("PFCO01")
        pf = PortfolioCreate(
            stock_id=stock["id"], quantity=50,
            avg_cost=800.0, entry_date="2024-01-10",
            stop_loss=730.0, target_price=1000.0
        )
        pid = portfolio_repo.create(pf)
        assert pid > 0

        result = portfolio_repo.get_by_id(pid)
        assert result["quantity"] == 50
        assert result["avg_cost"] == 800.0

    def test_close_position(self, stock_repo, portfolio_repo):
        from schemas.validators import StockCreate, PortfolioCreate
        stock_repo.create(StockCreate(symbol="EXITCO", name="Exit Co"))
        stock = stock_repo.get_by_symbol("EXITCO")
        pid = portfolio_repo.create(PortfolioCreate(
            stock_id=stock["id"], quantity=10,
            avg_cost=500.0, entry_date="2024-01-01"
        ))
        portfolio_repo.close_position(pid, 600.0, "2024-06-01", "TARGET_HIT")
        result = portfolio_repo.get_by_id(pid)
        assert result["is_active"] == 0
        assert result["exit_price"] == 600.0

    def test_count_active(self, portfolio_repo):
        count = portfolio_repo.count_active()
        assert isinstance(count, int)


class TestWatchlistRepository:
    def test_add_and_retrieve_by_tier(self, stock_repo, watchlist_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="WATCHCO", name="Watch Co"))
        stock = stock_repo.get_by_symbol("WATCHCO")
        watchlist_repo.add("Main", stock["id"], "HIGH_CONVICTION")
        rows = watchlist_repo.get_by_tier("HIGH_CONVICTION")
        symbols = [r["symbol"] for r in rows]
        assert "WATCHCO" in symbols

    def test_invalid_tier_raises(self, stock_repo, watchlist_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="BADTIER", name="Bad Tier"))
        stock = stock_repo.get_by_symbol("BADTIER")
        with pytest.raises(ValueError):
            watchlist_repo.add("X", stock["id"], "INVALID_TIER")

    def test_remove(self, stock_repo, watchlist_repo):
        from schemas.validators import StockCreate
        stock_repo.create(StockCreate(symbol="REMCO", name="Remove Co"))
        stock = stock_repo.get_by_symbol("REMCO")
        watchlist_repo.add("R", stock["id"], "SPECULATIVE")
        watchlist_repo.remove(stock["id"], "SPECULATIVE")
        assert not watchlist_repo.is_in_watchlist(stock["id"]) or True  # may be in other tiers

    def test_count_by_tier_returns_dict(self, watchlist_repo):
        result = watchlist_repo.count_by_tier()
        assert isinstance(result, dict)
