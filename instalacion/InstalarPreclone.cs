using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;

[assembly: AssemblyTitle("Instalar Preclone")]
[assembly: AssemblyProduct("Preclone")]

internal static class InstalarPreclone
{
    private const string PythonUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.zip";
    private const string PythonSha256 = "8649692DE846C56A7189D6DAE5C322AB20DEB1B5908B6F39426B62A36F39415D";

    private static int Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        Console.WriteLine("Instalar Preclone para Codex");
        try
        {
            var datos = Instalar(Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory));
            Console.WriteLine();
            Console.WriteLine("Preclone está listo para agregarlo desde los ajustes de servidores MCP.");
            Console.WriteLine("Abre Datos-MCP.txt en esta carpeta y copia sus datos.");
            Console.WriteLine();
            Console.WriteLine(datos);
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("No se pudo instalar Preclone. " + error.Message);
            return 1;
        }
        finally
        {
            if (!Console.IsInputRedirected && !Console.IsOutputRedirected)
            {
                Console.WriteLine("Pulsa Intro para cerrar.");
                Console.ReadLine();
            }
        }
    }

    private static string Instalar(string raiz)
    {
        var modelo = Path.Combine(raiz, "artefactos", "v3", "modelo.joblib");
        var servidor = Path.Combine(raiz, "instalacion", "iniciar_mcp.py");
        if (!File.Exists(Path.Combine(raiz, "AGENTS.md")) ||
            !File.Exists(Path.Combine(raiz, "pyproject.toml")) ||
            !File.Exists(modelo) || !File.Exists(servidor))
        {
            throw new IOException("Abre el instalador junto a AGENTS.md en la carpeta completa de Preclone.");
        }

        var git = BuscarGit();
        var local = Directory.CreateDirectory(Path.Combine(raiz, ".preclone")).FullName;
        var python = PrepararPython(raiz, local);
        var entorno = Path.Combine(local, "venv");
        var pythonEntorno = Path.Combine(entorno, "Scripts", "python.exe");
        Console.WriteLine("Preparando el entorno de Preclone.");
        var configuracion = Path.Combine(entorno, "pyvenv.cfg");
        var origen = "home = " + Path.GetDirectoryName(python);
        if (!File.Exists(pythonEntorno) || !File.Exists(configuracion) ||
            !File.ReadLines(configuracion).Contains(origen, StringComparer.OrdinalIgnoreCase))
        {
            Ejecutar(python, raiz, "-I", "-m", "venv", entorno);
        }
        else if (!File.Exists(Path.Combine(entorno, "Lib", "site-packages", "pip", "__init__.py")))
        {
            Ejecutar(pythonEntorno, raiz, "-I", "-m", "ensurepip");
        }
        Ejecutar(pythonEntorno, raiz, "-I", "-m", "pip", "--disable-pip-version-check",
            "install", "--no-input", "--cache-dir", Path.Combine(local, "pip-cache"), "-e", ".[mcp]");
        Ejecutar(pythonEntorno, raiz, "-I", "-c",
            "import sys; from pathlib import Path; from preclone.detector import Detector; import preclone.mcp; Detector.cargar(Path(sys.argv[1]))",
            modelo);

        File.WriteAllText(Path.Combine(local, "git.txt"), git, new UTF8Encoding(false));
        var datos = string.Join(Environment.NewLine, new[] {
            "Nombre: preclone",
            "Tipo: stdio",
            "Comando: " + pythonEntorno,
            "Argumento: " + servidor,
            ""
        });
        File.WriteAllText(Path.Combine(raiz, "Datos-MCP.txt"), datos, new UTF8Encoding(false));
        return datos;
    }

    private static string BuscarGit()
    {
        var rutas = (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';').ToList();
        rutas.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Git", "cmd"));
        rutas.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Programs", "Git", "cmd"));
        foreach (var ruta in rutas)
        {
            var directorio = ruta.Trim().Trim('"');
            if (directorio.Length < 3 || directorio[1] != ':' ||
                (directorio[2] != '\\' && directorio[2] != '/'))
                continue;
            var ejecutable = Path.Combine(directorio, "git.exe");
            if (File.Exists(ejecutable))
                return Path.GetFullPath(ejecutable);
        }
        throw new IOException("Instala Git para Windows y vuelve a abrir el instalador.");
    }

    private static string PrepararPython(string raiz, string local)
    {
        var destino = Path.Combine(local, "python");
        var python = Path.Combine(destino, "python.exe");
        if (File.Exists(python))
        {
            ComprobarPython(python, raiz);
            return python;
        }
        if (Directory.Exists(destino))
            throw new IOException("Ya existe una carpeta .preclone\\python incompleta. Muévela y vuelve a abrir el instalador.");

        var id = Guid.NewGuid().ToString("N");
        var archivo = Path.Combine(local, "python-" + id + ".zip");
        var temporal = Path.Combine(local, "python-" + id);
        try
        {
            Console.WriteLine("Descargando Python 3.12.10 para esta carpeta.");
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
            using (var cliente = new WebClient())
                cliente.DownloadFile(PythonUrl, archivo);
            using (var sha256 = SHA256.Create())
            using (var contenido = File.OpenRead(archivo))
            {
                var huella = BitConverter.ToString(sha256.ComputeHash(contenido)).Replace("-", "");
                if (!huella.Equals(PythonSha256, StringComparison.OrdinalIgnoreCase))
                    throw new IOException("La descarga de Python no coincide con el SHA-256 esperado.");
            }
            ZipFile.ExtractToDirectory(archivo, temporal);
            ComprobarPython(Path.Combine(temporal, "python.exe"), raiz);
            Directory.Move(temporal, destino);
            return python;
        }
        finally
        {
            if (Directory.Exists(temporal))
                Directory.Delete(temporal, true);
            File.Delete(archivo);
        }
    }

    private static void ComprobarPython(string python, string raiz)
    {
        Ejecutar(python, raiz, "-I", "-c",
            "import struct, sys, tkinter; assert sys.version_info[:3] == (3, 12, 10); assert struct.calcsize('P') == 8; tkinter.Tcl().eval('info patchlevel')");
    }

    private static void Ejecutar(string ejecutable, string directorio, params string[] argumentos)
    {
        // Windows no admite comillas en nombres de archivo. Los fragmentos de
        // Python usan comillas simples y cada argumento conserva sus espacios.
        var proceso = new ProcessStartInfo(ejecutable, string.Join(" ", argumentos.Select(a => "\"" + a + "\"")));
        proceso.WorkingDirectory = directorio;
        proceso.UseShellExecute = false;
        using (var hijo = Process.Start(proceso))
        {
            hijo.WaitForExit();
            if (hijo.ExitCode != 0)
                throw new IOException("Falló un paso de Python. Revisa el mensaje anterior y vuelve a intentarlo.");
        }
    }
}
