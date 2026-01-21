"""Integration tests for thread-safe database sessions.

These tests verify that database sessions work correctly in multi-threaded
environments, particularly for QThread-based import workers.

Critical Scenarios:
    1. Multiple threads can create independent sessions
    2. Sessions are properly isolated (no cross-thread corruption)
    3. Rollback in one thread doesn't affect others
    4. Sessions are properly closed on thread exit
"""

import pytest
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.session import thread_scoped_session, project_session_factory
from database.models import Base, Story, LoadCase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_threads.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    # Initialize the session factory for this db_path
    # Note: project_session_factory caches engines by path
    yield db_path
    
    engine.dispose()


class TestThreadScopedSession:
    """Tests for the thread_scoped_session context manager."""
    
    def test_creates_independent_sessions(self, temp_db):
        """Each call to thread_scoped_session creates a new session."""
        sessions_held = []
        lock = threading.Lock()

        def get_session_id():
            with thread_scoped_session(temp_db) as session:
                # Hold reference to prevent GC reusing ID
                with lock:
                    sessions_held.append(session)
                time.sleep(0.05)  # Ensure overlap so sessions exist simultaneously

        threads = [threading.Thread(target=get_session_id) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All sessions should be unique (checked while still holding references)
        session_ids = [id(s) for s in sessions_held]
        assert len(session_ids) == 5
        assert len(set(session_ids)) == 5, "Sessions should be unique per thread"
    
    def test_session_commits_on_success(self, temp_db):
        """Session should commit changes when no exception occurs."""
        project_id = 1
        story_name = "Test Story"
        
        with thread_scoped_session(temp_db) as session:
            story = Story(
                project_id=project_id,
                name=story_name,
                sort_order=1
            )
            session.add(story)
        
        # Verify in new session
        with thread_scoped_session(temp_db) as session:
            result = session.query(Story).filter_by(name=story_name).first()
            assert result is not None
            assert result.name == story_name
    
    def test_session_rollback_on_exception(self, temp_db):
        """Session should rollback on exception."""
        project_id = 1
        story_name = "Rollback Story"
        
        try:
            with thread_scoped_session(temp_db) as session:
                story = Story(
                    project_id=project_id,
                    name=story_name,
                    sort_order=1
                )
                session.add(story)
                session.flush()  # Write to DB
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Verify rollback in new session
        with thread_scoped_session(temp_db) as session:
            result = session.query(Story).filter_by(name=story_name).first()
            assert result is None, "Story should have been rolled back"
    
    def test_concurrent_writes_isolated(self, temp_db):
        """Concurrent threads should not interfere with each other's writes."""
        results = []
        errors = []
        
        def write_story(story_name):
            try:
                with thread_scoped_session(temp_db) as session:
                    story = Story(
                        project_id=1,
                        name=story_name,
                        sort_order=1
                    )
                    session.add(story)
                    time.sleep(0.01)  # Simulate work
                results.append(story_name)
            except Exception as e:
                errors.append(str(e))
        
        story_names = [f"Story_{i}" for i in range(10)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_story, name) for name in story_names]
            for future in as_completed(futures):
                future.result()  # Re-raise any exceptions
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # Verify all stories were written
        with thread_scoped_session(temp_db) as session:
            count = session.query(Story).count()
            assert count == 10
    
    def test_mixed_success_and_failure(self, temp_db):
        """Some threads succeed, some fail - verify isolation."""
        successful = []
        failed = []
        
        def write_with_possible_failure(story_name, should_fail):
            try:
                with thread_scoped_session(temp_db) as session:
                    story = Story(
                        project_id=1,
                        name=story_name,
                        sort_order=1
                    )
                    session.add(story)
                    session.flush()
                    
                    if should_fail:
                        raise ValueError(f"Simulated failure for {story_name}")
                
                successful.append(story_name)
            except ValueError:
                failed.append(story_name)
        
        # Half succeed, half fail
        tasks = [(f"Success_{i}", False) for i in range(5)]
        tasks += [(f"Fail_{i}", True) for i in range(5)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(write_with_possible_failure, name, fail)
                for name, fail in tasks
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass  # We handle failures in the function
        
        assert len(successful) == 5
        assert len(failed) == 5
        
        # Verify only successful writes persist
        with thread_scoped_session(temp_db) as session:
            count = session.query(Story).count()
            assert count == 5
            
            # Verify the right ones persisted
            for name in successful:
                story = session.query(Story).filter_by(name=name).first()
                assert story is not None


class TestProjectSessionFactory:
    """Tests for the project_session_factory function."""
    
    def test_returns_session_maker(self, temp_db):
        """project_session_factory should return a sessionmaker."""
        factory = project_session_factory(temp_db)
        session = factory()
        
        try:
            # Should be able to execute queries
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            session.close()
    
    def test_same_path_same_engine(self, temp_db):
        """Same path should return same underlying engine (cached)."""
        factory1 = project_session_factory(temp_db)
        factory2 = project_session_factory(temp_db)
        
        # Both factories should use the same engine
        session1 = factory1()
        session2 = factory2()
        
        try:
            # Both should connect to the same database
            assert session1.get_bind().url == session2.get_bind().url
        finally:
            session1.close()
            session2.close()


class TestImportWorkerPattern:
    """Test the pattern used by import workers."""
    
    def test_worker_pattern_simulation(self, temp_db):
        """Simulate the import worker pattern with thread_scoped_session."""
        import_results = {}
        
        def simulate_import_worker(worker_id, db_path, load_cases):
            """Simulate what an import worker does."""
            try:
                with thread_scoped_session(db_path) as session:
                    # Create entities
                    for case_name in load_cases:
                        load_case = LoadCase(
                            project_id=worker_id,
                            name=case_name,
                            case_type="Test"
                        )
                        session.add(load_case)
                    
                    # Simulate import processing
                    time.sleep(0.02)
                    
                    # Session commits automatically on exit
                
                import_results[worker_id] = {"success": True, "count": len(load_cases)}
                
            except Exception as e:
                import_results[worker_id] = {"success": False, "error": str(e)}
        
        # Simulate multiple workers importing simultaneously
        worker_configs = [
            (1, ["PX1", "PX2"]),
            (2, ["PY1", "PY2", "PY3"]),
            (3, ["Case1"]),
        ]
        
        threads = [
            threading.Thread(
                target=simulate_import_worker,
                args=(worker_id, temp_db, load_cases)
            )
            for worker_id, load_cases in worker_configs
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify all workers succeeded
        assert all(r["success"] for r in import_results.values())
        
        # Verify correct counts
        with thread_scoped_session(temp_db) as session:
            for worker_id, load_cases in worker_configs:
                count = session.query(LoadCase).filter_by(project_id=worker_id).count()
                assert count == len(load_cases)
