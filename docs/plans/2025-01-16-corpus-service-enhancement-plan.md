# Corpus Service Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich corpus-lucene-service with unit/integration tests and restart the service

**Architecture:**
- Add HTTP handler tests using embedded Jetty test framework
- Add IndexBuilder integration tests with H2 in-memory database
- Rebuild and restart the service on Windows

**Tech Stack:** Java 17, JUnit 5, Mockito, H2 Database, Lucene 9.11.1, Jetty 11

---

## Plan Summary

| Task | Description |
|------|-------------|
| 1 | Analyze existing tests and service structure |
| 2 | Create HTTP Handler integration tests |
| 3 | Create IndexBuilder tests with H2 database |
| 4 | Update pom.xml with test dependencies if needed |
| 5 | Build and run all tests |
| 6 | Rebuild JAR with Maven |
| 7 | Stop old service and restart with new JAR |

---

## Task 1: Analyze Existing Tests

**Files:**
- Read: `src/test/java/pl/wielki/corpus/SearchServiceTest.java`
- Read: `src/test/java/pl/wielki/corpus/ExactTokenAnalyzerTest.java`
- Read: `pom.xml`

**Goal:** Understand existing test patterns and dependencies

---

## Task 2: Create HTTP Handler Integration Tests

**Files:**
- Create: `src/test/java/pl/wielki/corpus/HandlerIntegrationTest.java`

**Step 1: Write the failing test**

```java
package pl.wielki.corpus;

import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.junit.jupiter.api.*;
import org.mockito.Mockito;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;

import static org.junit.jupiter.api.Assertions.*;

public class HandlerIntegrationTest {

    private SearchService searchService;

    @BeforeEach
    void setUp() throws Exception {
        // Use test index path or create temporary index
        searchService = new SearchService(java.nio.file.Path.of("target/test-index"));
    }

    @AfterEach
    void tearDown() throws Exception {
        if (searchService != null) {
            searchService.close();
        }
    }

    @Test
    void countHandler_returnsCorrectCount() throws Exception {
        // Test CountHandler with mock request/response
        CountHandler handler = new CountHandler(searchService);

        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        HttpServletResponse response = Mockito.mock(HttpServletResponse.class);

        Mockito.when(request.getParameter("q")).thenReturn("test");
        Mockito.when(request.getParameter("field")).thenReturn("en");

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintWriter writer = new PrintWriter(out);
        Mockito.when(response.getWriter()).thenReturn(writer);

        handler.doGet(request, response);
        writer.flush();

        String result = out.toString();
        assertTrue(result.contains("count"));
    }

    @Test
    void healthHandler_returnsStatus() throws Exception {
        HealthHandler handler = new HealthHandler(searchService);

        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        HttpServletResponse response = Mockito.mock(HttpServletResponse.class);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintWriter writer = new PrintWriter(out);
        Mockito.when(response.getWriter()).thenReturn(writer);

        handler.doGet(request, response);
        writer.flush();

        String result = out.toString();
        assertTrue(result.contains("status"));
        assertTrue(result.contains("docs"));
    }
}
```

**Step 2: Try to compile and run test**

Run: `mvn test -Dtest=HandlerIntegrationTest`
Expected: FAIL - class not found (file doesn't exist)

**Step 3: Create the test file with imports fixed**

Create the file at `src/test/java/pl/wielki/corpus/HandlerIntegrationTest.java`

**Step 4: Run test to verify it works**

Run: `mvn test -Dtest=HandlerIntegrationTest`
Expected: Tests may fail due to missing index - adjust setUp to build index first

**Step 5: Commit**

```bash
git add src/test/java/pl/wielki/corpus/HandlerIntegrationTest.java
git commit -m "test: add HTTP handler integration tests"
```

---

## Task 3: Create IndexBuilder Tests with H2

**Files:**
- Create: `src/test/java/pl/wielki/corpus/IndexBuilderTest.java`

**Step 1: Write the failing test**

```java
package pl.wielki.corpus;

import org.junit.jupiter.api.*;
import java.nio.file.*;
import java.sql.*;

import static org.junit.jupiter.api.Assertions.*;

public class IndexBuilderTest {

    private Path tempDir;

    @BeforeEach
    void setUp() throws Exception {
        tempDir = Files.createTempDirectory("lucene-test-");
    }

    @AfterEach
    void tearDown() throws Exception {
        // Cleanup temp directory
    }

    @Test
    void indexBuilder_createsValidIndex() throws Exception {
        // Create H2 in-memory database with test data
        String jdbcUrl = "jdbc:h2:mem:testdb";

        // Insert test data
        try (Connection conn = DriverManager.getConnection(jdbcUrl, "sa", "")) {
            conn.createStatement().execute(
                "CREATE TABLE parallel_corpus AS " +
                "SELECT 'hello world' AS source_text, 'witaj swiecie' AS target_text " +
                "UNION ALL " +
                "SELECT 'good morning', 'dzien dobry'"
            );
        }

        // Build index
        IndexBuilder builder = new IndexBuilder(jdbcUrl, "", "", tempDir);
        long count = builder.build("SELECT source_text, target_text FROM parallel_corpus");

        assertEquals(2, count);

        // Verify index can be opened
        SearchService searchService = new SearchService(tempDir);
        assertEquals(2, searchService.getDocCount());
        searchService.close();
    }
}
```

**Step 2: Check pom.xml for H2 dependency**

Read `pom.xml` - add H2 if not present

**Step 3: Create test file**

Create `src/test/java/pl/wielki/corpus/IndexBuilderTest.java`

**Step 4: Run test**

Run: `mvn test -Dtest=IndexBuilderTest`
Expected: PASS

**Step 5: Commit**

```bash
git add src/test/java/pl/wielki/corpus/IndexBuilderTest.java
git commit -m "test: add IndexBuilder integration tests with H2"
```

---

## Task 4: Add H2 Dependency to pom.xml

**Files:**
- Modify: `pom.xml`

**Step 1: Add H2 dependency**

```xml
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <version>2.2.224</version>
    <scope>test</scope>
</dependency>
```

**Step 2: Verify Maven can resolve**

Run: `mvn dependency:resolve`
Expected: H2 downloaded

**Step 3: Run all tests**

Run: `mvn test`
Expected: All tests pass

**Step 4: Commit**

```bash
git add pom.xml
git commit -m "chore: add H2 test dependency"
```

---

## Task 5: Build and Run All Tests

**Files:**
- No file changes

**Step 1: Run full test suite**

Run: `mvn clean test`
Expected: All tests pass (SearchServiceTest, ExactTokenAnalyzerTest, HandlerIntegrationTest, IndexBuilderTest)

**Step 2: Package JAR**

Run: `mvn clean package -DskipTests`
Expected: JAR built successfully at `target/corpus-lucene-service-*.jar`

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: run tests and build JAR"
```

---

## Task 6: Stop Old Service and Restart

**Files:**
- No file changes (operational)

**Step 1: Find running service PID**

On Windows PowerShell:
```powershell
netstat -ano | findstr :8082
```

**Step 2: Stop old service**

```powershell
taskkill /PID <PID> /F
```

**Step 3: Start new service**

```powershell
java -Xmx4g -jar target/corpus-lucene-service-*.jar serve --index D:\path\to\index --port 8082
```

**Step 4: Verify binding**

```powershell
netstat -ano | findstr :8082
```

Expected: `TCP    0.0.0.0:8082    0.0.0.0:0    LISTENING`

**Step 5: Test health endpoint**

```bash
curl http://localhost:8082/health
```

Expected: JSON with status, docs count

---

## Task 7: Verify Flask Integration

**Files:**
- No changes

**Step 1: Test from WSL**

```bash
curl http://172.17.96.1:8082/health
```

**Step 2: Test Flask app**

Visit: `http://localhost:5000/corpus-management`

Verify:
- Total records shown (~74.7M)
- Last updated timestamp
- Connection status connected

---

## Notes

### Existing Tests
- `ExactTokenAnalyzerTest.java` - 7 tests for tokenization
- `SearchServiceTest.java` - 8 integration tests for search service

### Handler Endpoints
- `GET /count?q={term}&field={en|pl}` - count documents
- `POST /compare` - compare term frequencies
- `GET /concordance?q={term}&field={en|pl}&limit&offset` - parallel text
- `GET /parallel?en={term}&pl={term}&limit` - cross-language search
- `GET /health` - health check with doc count

### Expected Test Coverage After Implementation
- Unit tests: ExactTokenAnalyzer (7 tests)
- Integration tests: SearchService (8 tests)
- Handler tests: HTTP layer (2-3 tests)
- IndexBuilder tests: H2 integration (1-2 tests)
- **Total: 18-20 tests**
