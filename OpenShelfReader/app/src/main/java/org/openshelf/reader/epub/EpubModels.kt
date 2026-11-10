package org.openshelf.reader.epub

data class EpubManifest(
    val title: String?,
    val author: String?,
    val chapters: List<EpubChapter>,
    val toc: List<EpubTocItem>
)

data class EpubChapter(
    val id: String,
    val title: String,
    val absolutePath: String
)

data class EpubTocItem(
    val title: String,
    val href: String,
    val absolutePath: String?
)

internal data class ManifestItem(
    val id: String,
    val href: String,
    val mediaType: String?,
    val properties: String?
)
