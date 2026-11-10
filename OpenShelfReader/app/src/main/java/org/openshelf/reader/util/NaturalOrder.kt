package org.openshelf.reader.util

/**
 * Comparación de orden natural para nombres de archivo de páginas de cómic:
 * "page2.jpg" < "page10.jpg" (el orden lexicográfico normal pondría page10 antes que page2).
 */
fun naturalCompare(a: String, b: String): Int {
    var i = 0
    var j = 0

    while (i < a.length && j < b.length) {
        val ca = a[i]
        val cb = b[j]

        if (ca.isDigit() && cb.isDigit()) {
            var ia = i
            while (ia < a.length && a[ia].isDigit()) ia++
            var jb = j
            while (jb < b.length && b[jb].isDigit()) jb++

            // Comparar dígitos sin ceros a la izquierda: más dígitos = número mayor
            val na = a.substring(i, ia).trimStart('0')
            val nb = b.substring(j, jb).trimStart('0')

            if (na.length != nb.length) return na.length - nb.length
            val cmp = na.compareTo(nb)
            if (cmp != 0) return cmp

            i = ia
            j = jb
        } else {
            val cmp = ca.lowercaseChar().compareTo(cb.lowercaseChar())
            if (cmp != 0) return cmp

            i++
            j++
        }
    }

    return (a.length - i) - (b.length - j)
}
