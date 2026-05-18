@echo off
REM run_pipeline.bat — Sets Java 17 + Hadoop, then runs the pipeline
REM Usage: run_pipeline.bat bronze | silver | gold | all

REM Force Java 17
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
set "PATH=%JAVA_HOME%\bin;%PATH%"

REM Force Hadoop home
set "HADOOP_HOME=%~dp0hadoop"
set "PATH=%HADOOP_HOME%\bin;%PATH%"

echo ==========================================
echo  Healthcare Data Lakehouse Pipeline
echo ==========================================
echo JAVA_HOME  = %JAVA_HOME%
echo HADOOP_HOME = %HADOOP_HOME%

REM Verify Java version
echo.
echo Java version:
java -version 2>&1 | findstr /i "version"
echo.

REM Check what to run
if "%1"=="" (
    echo Usage: run_pipeline.bat [bronze^|silver^|gold^|all]
    echo.
    echo   bronze  - Ingest raw CSV/JSONL to Delta Lake
    echo   silver  - Cleanse, deduplicate, mask PHI
    echo   gold    - Build star schema dimensions + facts
    echo   all     - Run full pipeline (bronze then silver then gold)
    exit /b 0
)

if /i "%1"=="bronze" (
    echo Running Bronze ingestion...
    python -m src.transformations.bronze.ingest
    goto :done
)

if /i "%1"=="silver" (
    echo Running Silver transformations...
    python -m src.transformations.silver.transform
    goto :done
)

if /i "%1"=="gold" (
    echo Running Gold dimensions...
    python -m src.transformations.gold.build_dimensions
    goto :done
)

if /i "%1"=="all" (
    echo Running full pipeline: Bronze -^> Silver -^> Gold
    echo.
    echo [1/3] Bronze ingestion...
    python -m src.transformations.bronze.ingest
    if errorlevel 1 goto :fail
    echo.
    echo [2/3] Silver transformations...
    python -m src.transformations.silver.transform
    if errorlevel 1 goto :fail
    echo.
    echo [3/3] Gold dimensions...
    python -m src.transformations.gold.build_dimensions
    if errorlevel 1 goto :fail
    goto :done
)

echo Unknown command: %1
exit /b 1

:fail
echo.
echo PIPELINE FAILED at the step above.
exit /b 1

:done
echo.
echo Pipeline step complete!
exit /b 0
