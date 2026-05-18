!define PRODUCT_NAME "Ring"
!define PRODUCT_PUBLISHER "iiishop"

Name "${PRODUCT_NAME} ${VERSION}"
OutFile "..\Ring-${VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
RequestExecutionLevel admin

Section "Install"
  SetOutPath "$INSTDIR"
  File /oname=Ring.exe "${RING_EXE}"

  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Ring.lnk" "$INSTDIR\Ring.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayVersion" "${VERSION}"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Ring.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  Delete "$INSTDIR\Ring.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd
