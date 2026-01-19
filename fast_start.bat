@echo off
setlocal
pushd %~dp0

echo [1/3] Changing line endings to LF (No BOM)...
:: BOM 없이 저장하기 위해 .NET 클래스를 직접 호출하는 PowerShell 명령어를 사용합니다.
powershell -Command "$c1 = [System.IO.File]::ReadAllText('init-db.sh').Replace(\"`r`n\", \"`n\"); [System.IO.File]::WriteAllText('init-db.sh', $c1, (New-Object System.Text.UTF8Encoding($false)))"
powershell -Command "$c2 = [System.IO.File]::ReadAllText('init-data.sh').Replace(\"`r`n\", \"`n\"); [System.IO.File]::WriteAllText('init-data.sh', $c2, (New-Object System.Text.UTF8Encoding($false)))"
echo [OK] Line endings converted without BOM.

echo.
echo [2/3] Docker Compose Down (with volumes)...
docker compose down --rmi all -v

echo.
echo [3/3] Docker Compose Up (Build and Detach)...
docker compose up --build -d

echo.
echo ==========================================
echo [DONE] All processes completed successfully!
echo ==========================================
pause

popd
endlocal