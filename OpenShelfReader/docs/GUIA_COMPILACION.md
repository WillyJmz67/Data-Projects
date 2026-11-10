# Guía de compilación — OpenShelf Reader

Guía práctica para compilar el proyecto, generar el APK y publicarlo en GitHub Releases.

## 1. Requisitos

| Herramienta | Versión | Notas |
|---|---|---|
| JDK | 17 | Necesario para AGP 8.5. En Android Studio: Settings → Build Tools → Gradle → Gradle JDK |
| Android SDK | API 34 | Lo instala Android Studio automáticamente |
| Android Studio | Koala o superior | Recomendado para desarrollar |
| Gradle | 8.9 | Incluido vía wrapper (`./gradlew`), no necesitas instalarlo |

> Nota: si tu máquina tiene un JDK más nuevo (por ejemplo Java 25) como JDK por defecto del sistema, no pasa nada siempre que Gradle use JDK 17 (configúralo en Android Studio o con `org.gradle.java.home`).

## 2. Instalar Android Studio

1. Descarga desde https://developer.android.com/studio.
2. Durante la instalación acepta: Android SDK, Android SDK Platform y (opcional) un emulador.

## 3. Abrir y sincronizar el proyecto

1. Android Studio → **Open** → selecciona la carpeta `OpenShelfReader`.
2. Espera a que sincronice Gradle (la primera vez descarga dependencias: Compose, Room, WorkManager, OkHttp, Coil, Navigation… puede tardar varios minutos).
3. Si pide JDK: **File → Settings → Build, Execution, Deployment → Build Tools → Gradle → Gradle JDK = 17**.

## 4. Compilar

### Desde Android Studio
- Botón **Run ▶** para compilar e instalar en emulador/móvil conectado.

### Desde la terminal (en la raíz del proyecto)

Linux / macOS:
```bash
./gradlew assembleDebug
```

Windows (CMD o PowerShell):
```cmd
gradlew.bat assembleDebug
```

El APK debug queda en:
```text
app/build/outputs/apk/debug/app-debug.apk
```

## 5. Instalar el APK debug en un móvil

Con el móvil conectado por USB y la depuración USB activada:
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

O copia el APK al móvil y ábrelo desde el explorador de archivos.

## 6. Generar APK de release firmado (para distribuir)

### 6.1 Crear el keystore (una sola vez)

```bash
keytool -genkey -v \
  -keystore openshelf.keystore \
  -alias openshelf \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

> Guarda el keystore y las contraseñas en lugar seguro. Si los pierdes, no podrás publicar actualizaciones con la misma firma.

### 6.2 Compilar release con firma (local)

Linux / macOS:
```bash
export VERSION_NAME=0.1.0
export VERSION_CODE=1
export KEYSTORE_PATH=/ruta/segura/openshelf.keystore
export KEYSTORE_PASSWORD="TU_PASSWORD"
export KEY_ALIAS="openshelf"
export KEY_PASSWORD="TU_PASSWORD"

./gradlew assembleRelease
```

Windows (PowerShell):
```powershell
$env:VERSION_NAME="0.1.0"
$env:VERSION_CODE="1"
$env:KEYSTORE_PATH="C:\ruta\segura\openshelf.keystore"
$env:KEYSTORE_PASSWORD="TU_PASSWORD"
$env:KEY_ALIAS="openshelf"
$env:KEY_PASSWORD="TU_PASSWORD"

.\gradlew.bat assembleRelease
```

El APK queda en:
```text
app/build/outputs/apk/release/app-release.apk
```

Si no configuras las variables del keystore, el release se firma con la clave debug (útil para pruebas, no para distribuir).

## 7. Publicar en GitHub (automático con Actions)

El proyecto incluye `.github/workflows/android-release.yml`.

### 7.1 Subir el proyecto a GitHub

```bash
git init
git add .
git commit -m "Proyecto inicial OpenShelf Reader"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/OpenShelfReader.git
git push -u origin main
```

> Asegúrate de que el keystore NO está en el repo (el `.gitignore` ya lo excluye: `*.keystore`, `*.jks`, `*.base64`).

### 7.2 Configurar los secretos de firma

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Nombre | Valor |
|---|---|
| `KEYSTORE_BASE64` | Contenido de `openshelf.keystore` codificado en Base64 (`base64 -w 0 openshelf.keystore`) |
| `KEYSTORE_PASSWORD` | Contraseña del keystore |
| `KEY_ALIAS` | `openshelf` |
| `KEY_PASSWORD` | Contraseña de la clave |

Sin secretos el workflow también funciona: compila y publica el APK firmado con la clave debug.

### 7.3 Lanzar una release

```bash
git tag -a v0.1.0 -m "OpenShelf Reader v0.1.0"
git push origin v0.1.0
```

GitHub Actions compilará, firmará y publicará en Releases:
```text
OpenShelfReader-0.1.0.apk
OpenShelfReader-0.1.0.apk.sha256
```

## 8. Errores comunes

| Error | Solución |
|---|---|
| `SDK location not found` | Crea `local.properties` en la raíz con `sdk.dir=C:\\Users\\TU_USUARIO\\AppData\\Local\\Android\\Sdk` (Windows). No lo subas a GitHub. |
| `Unsupported class file major version` | Gradle está usando un JDK equivocado. Usa JDK 17 (Gradle JDK en Android Studio). |
| `Unresolved reference` | Falta un import o el archivo no está en el paquete correcto: el `package org.openshelf.reader...` del archivo debe coincidir con su carpeta. |
| Recurso `@mipmap/ic_launcher` no encontrado | No borres `app/src/main/res/`. El proyecto usa iconos adaptativos en `mipmap-anydpi-v26`. |
| Error de Room | Revisa que las entidades estén registradas en `OpenShelfDatabase`. |
| Timeout de red al sincronizar Gradle | Reintenta el sync; usa VPN/proxy si tu red bloquea repos de Google/Maven. |

## 9. Verificar integridad de un APK descargado

Cada release incluye un checksum SHA-256:
```bash
sha256sum OpenShelfReader-0.1.0.apk
# compara con el contenido de OpenShelfReader-0.1.0.apk.sha256
```
