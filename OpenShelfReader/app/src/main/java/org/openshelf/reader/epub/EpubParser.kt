package org.openshelf.reader.epub

import org.openshelf.reader.util.naturalCompare
import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.io.File
import java.io.FileInputStream
import java.net.URLDecoder
import java.util.zip.ZipInputStream

/**
 * Parser de EPUB:
 * 1. Descomprime el archivo (ZIP) en un directorio de trabajo, con protección zip-slip.
 * 2. Lee META-INF/container.xml para localizar el OPF.
 * 3. Lee el OPF (spine + manifest) para construir la lista de capítulos.
 * 4. Lee el NCX (tabla de contenidos) si existe.
 */
object EpubParser {

    fun parse(epubFile: File, destDir: File): EpubManifest {
        val marker = File(destDir, ".extracted")

        if (!marker.exists()) {
            destDir.deleteRecursively()
            unzip(epubFile, destDir)
            marker.createNewFile()
        }

        return parseExtracted(destDir)
    }

    private fun unzip(epubFile: File, destDir: File) {
        destDir.mkdirs()
        val canonicalDest = destDir.canonicalPath

        FileInputStream(epubFile).use { fis ->
            ZipInputStream(fis).use { zis ->
                var entry = zis.nextEntry

                while (entry != null) {
                    val outFile = File(destDir, entry.name)

                    // Protección zip-slip: no permitir rutas fuera del directorio destino
                    if (!outFile.canonicalPath.startsWith(canonicalDest)) {
                        zis.closeEntry()
                        entry = zis.nextEntry
                        continue
                    }

                    if (entry.isDirectory) {
                        outFile.mkdirs()
                    } else {
                        outFile.parentFile?.mkdirs()
                        outFile.outputStream().use { out ->
                            zis.copyTo(out)
                        }
                    }

                    zis.closeEntry()
                    entry = zis.nextEntry
                }
            }
        }
    }

    private fun parseExtracted(destDir: File): EpubManifest {
        val containerFile = File(destDir, "META-INF/container.xml")
        if (!containerFile.exists()) {
            return fallbackScan(destDir, title = "Libro Local", author = "Desconocido")
        }

        val opfPath = parseContainer(containerFile)
        val opfFile = if (opfPath != null) File(destDir, opfPath) else null

        if (opfFile != null && opfFile.exists()) {
            return parseOpf(opfFile, destDir)
        }

        return fallbackScan(destDir, title = "Libro Local", author = "Desconocido")
    }

    private fun XmlPullParser.attr(name: String): String? {
        for (i in 0 until attributeCount) {
            if (getAttributeName(i).equals(name, ignoreCase = true)) {
                return getAttributeValue(i)
            }
        }
        return null
    }

    private fun parseContainer(containerFile: File): String? {
        return runCatching {
            val factory = XmlPullParserFactory.newInstance()
            val parser = factory.newPullParser()
            parser.setInput(FileInputStream(containerFile), "UTF-8")

            var event = parser.eventType

            while (event != XmlPullParser.END_DOCUMENT) {
                val name = parser.name?.substringAfterLast(':') ?: ""

                if (event == XmlPullParser.START_TAG && name.equals("rootfile", ignoreCase = true)) {
                    val fullPath = parser.attr("full-path")
                    if (!fullPath.isNullOrBlank()) return fullPath
                }

                event = parser.next()
            }
            null
        }.getOrNull()
    }

    private fun parseOpf(opfFile: File, destDir: File): EpubManifest {
        val opfDir = opfFile.parentFile ?: destDir

        val factory = XmlPullParserFactory.newInstance()
        val parser = factory.newPullParser()
        parser.setInput(FileInputStream(opfFile), null)

        var title: String? = null
        var author: String? = null

        val manifest = mutableMapOf<String, ManifestItem>()
        val spineIds = mutableListOf<String>()

        var tocId: String? = null
        var ncxHref: String? = null

        var event = parser.eventType

        while (event != XmlPullParser.END_DOCUMENT) {
            val name = parser.name?.substringAfterLast(':') ?: ""

            if (event == XmlPullParser.START_TAG) {
                when {
                    name.equals("title", ignoreCase = true) -> {
                        if (title == null) {
                            runCatching { title = parser.nextText()?.trim() }
                        }
                    }

                    name.equals("creator", ignoreCase = true) -> {
                        if (author == null) {
                            runCatching { author = parser.nextText()?.trim() }
                        }
                    }

                    name.equals("item", ignoreCase = true) -> {
                        val id = parser.attr("id")
                        val href = parser.attr("href")
                        val mediaType = parser.attr("media-type")
                        val properties = parser.attr("properties")

                        if (id != null && href != null) {
                            manifest[id] = ManifestItem(
                                id = id,
                                href = href,
                                mediaType = mediaType,
                                properties = properties
                            )

                            if (mediaType.equals("application/x-dtbncx+xml", ignoreCase = true)) {
                                ncxHref = href
                            }
                        }
                    }

                    name.equals("itemref", ignoreCase = true) -> {
                        val idref = parser.attr("idref")
                        if (idref != null) {
                            spineIds.add(idref)
                        }
                    }

                    name.equals("spine", ignoreCase = true) -> {
                        tocId = parser.attr("toc")
                    }
                }
            }

            event = parser.next()
        }

        fun decodePath(path: String): String {
            return runCatching { URLDecoder.decode(path, "UTF-8") }.getOrDefault(path)
        }

        fun resolveHref(href: String, baseDir: File): File {
            val clean = decodePath(href.substringBefore('#'))
            val file = if (clean.startsWith("/")) {
                File(destDir, clean.trimStart('/'))
            } else {
                File(baseDir, clean)
            }
            return file.canonicalFile
        }

        val spineChapters = spineIds.mapIndexedNotNull { index, idRef ->
            val item = manifest[idRef] ?: return@mapIndexedNotNull null
            val file = resolveHref(item.href, opfDir)

            if (file.exists()) {
                EpubChapter(
                    id = "chapter_$index",
                    title = "Capítulo ${index + 1}",
                    absolutePath = file.absolutePath
                )
            } else {
                null
            }
        }

        val chapters = if (spineChapters.isNotEmpty()) {
            spineChapters
        } else {
            fallbackScan(destDir, title, author).chapters
        }

        val ncxFile = when {
            tocId != null && manifest[tocId] != null -> {
                resolveHref(manifest[tocId]!!.href, opfDir)
            }

            ncxHref != null -> resolveHref(ncxHref, opfDir)

            else -> null
        }

        val toc = if (ncxFile != null && ncxFile.exists()) {
            parseNcx(ncxFile, destDir)
        } else {
            emptyList()
        }

        return EpubManifest(
            title = title,
            author = author,
            chapters = chapters,
            toc = toc
        )
    }

    private fun parseNcx(ncxFile: File, destDir: File): List<EpubTocItem> {
        return runCatching {
            val factory = XmlPullParserFactory.newInstance()
            val parser = factory.newPullParser()
            parser.setInput(FileInputStream(ncxFile), null)

            val items = mutableListOf<EpubTocItem>()

            var insideNavPoint = 0
            var insideNavLabel = false

            var currentTitle: String? = null
            var currentSrc: String? = null

            var event = parser.eventType

            while (event != XmlPullParser.END_DOCUMENT) {
                val name = parser.name?.substringAfterLast(':') ?: ""

                when (event) {
                    XmlPullParser.START_TAG -> {
                        when {
                            name.equals("navPoint", ignoreCase = true) -> {
                                insideNavPoint++
                                currentTitle = null
                                currentSrc = null
                            }

                            name.equals("navLabel", ignoreCase = true) -> {
                                insideNavLabel = true
                            }

                            name.equals("text", ignoreCase = true) -> {
                                if (insideNavLabel && insideNavPoint > 0 && currentTitle == null) {
                                    currentTitle = parser.nextText()?.trim()
                                }
                            }

                            name.equals("content", ignoreCase = true) -> {
                                if (insideNavPoint > 0) {
                                    currentSrc = parser.attr("src")
                                }
                            }
                        }
                    }

                    XmlPullParser.END_TAG -> {
                        when {
                            name.equals("navLabel", ignoreCase = true) -> {
                                insideNavLabel = false
                            }

                            name.equals("navPoint", ignoreCase = true) -> {
                                if (currentTitle != null && currentSrc != null) {
                                    val cleanSrc = currentSrc!!.substringBefore('#')
                                    val target = if (cleanSrc.startsWith("/")) {
                                        File(destDir, cleanSrc.trimStart('/'))
                                    } else {
                                        File(ncxFile.parentFile, cleanSrc)
                                    }

                                    items.add(
                                        EpubTocItem(
                                            title = currentTitle!!,
                                            href = cleanSrc,
                                            absolutePath = if (target.exists()) target.absolutePath else null
                                        )
                                    )
                                }

                                insideNavPoint--
                                currentTitle = null
                                currentSrc = null
                            }
                        }
                    }
                }

                event = parser.next()
            }

            items
        }.getOrDefault(emptyList())
    }

    private fun fallbackScan(destDir: File, title: String?, author: String?): EpubManifest {
        val files = destDir.walkTopDown()
            .filter { it.isFile && (it.extension.lowercase() == "html" || it.extension.lowercase() == "xhtml" || it.extension.lowercase() == "htm") }
            .sortedWith { a, b -> naturalCompare(a.name, b.name) }
            .toList()

        val chapters = files.mapIndexed { index, file ->
            EpubChapter(
                id = "fallback_$index",
                title = "Página ${index + 1}",
                absolutePath = file.absolutePath
            )
        }

        return EpubManifest(
            title = title,
            author = author,
            chapters = chapters,
            toc = emptyList()
        )
    }
}
