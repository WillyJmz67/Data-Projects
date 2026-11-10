package org.openshelf.reader.util

import org.junit.Assert.assertTrue
import org.junit.Test

class NaturalOrderTest {

    @Test
    fun testNaturalCompare() {
        val files = listOf("page10.jpg", "page2.jpg", "page1.jpg", "page20.jpg")
        val sorted = files.sortedWith { a, b -> naturalCompare(a, b) }
        val expected = listOf("page1.jpg", "page2.jpg", "page10.jpg", "page20.jpg")
        assertTrue(sorted == expected)
    }

    @Test
    fun testNaturalCompareLeadingZeros() {
        assertTrue(naturalCompare("page01.jpg", "page2.jpg") < 0)
        assertTrue(naturalCompare("page2.jpg", "page10.jpg") < 0)
    }
}
