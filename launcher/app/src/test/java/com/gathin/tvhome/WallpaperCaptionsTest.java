package com.gathin.tvhome;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Map;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class WallpaperCaptionsTest {
    @Rule public TemporaryFolder folder = new TemporaryFolder();

    @Test
    public void readsFilenameTabName() {
        Map<String, String> names = WallpaperCaptions.parse(Arrays.asList(
                "001.jpg\tRed Spider Nebula · Hubble",
                "002.jpg\t  Falcon 9 at sunset  "));
        assertEquals("Red Spider Nebula · Hubble", names.get("001.jpg"));
        assertEquals("Falcon 9 at sunset", names.get("002.jpg"));
    }

    @Test
    public void skipsCommentsBlankAndMalformedLines() {
        Map<String, String> names = WallpaperCaptions.parse(Arrays.asList(
                "# captions for the collection", "", "   ", "no-tab-here.jpg Dusk", "\tno file", "003.jpg\t", null));
        assertTrue(names.isEmpty());
    }

    @Test
    public void cutsVeryLongNames() {
        StringBuilder longName = new StringBuilder();
        for (int i = 0; i < 30; i++) longName.append("word ");
        Map<String, String> names = WallpaperCaptions.parse(Arrays.asList("004.jpg\t" + longName));
        assertTrue(names.get("004.jpg").length() <= WallpaperCaptions.MAX_LENGTH);
    }

    @Test
    public void laterLineWinsForTheSameFile() {
        Map<String, String> names = WallpaperCaptions.parse(Arrays.asList("005.jpg\tOld", "005.jpg\tNew"));
        assertEquals("New", names.get("005.jpg"));
        assertFalse(names.containsKey("006.jpg"));
    }

    @Test
    public void missingFolderHasNoNames() {
        assertTrue(WallpaperCaptions.read(null).isEmpty());
    }

    @Test
    public void readsUtf8FileWithMixedLineEndings() throws Exception {
        File captions = folder.newFile(WallpaperCaptions.FILE_NAME);
        try (FileOutputStream out = new FileOutputStream(captions)) {
            out.write(("# collection\r\n001.jpg\t星空\r\nmalformed\n002.jpg\tDawn")
                    .getBytes(StandardCharsets.UTF_8));
        }
        Map<String, String> names = WallpaperCaptions.read(folder.getRoot());
        assertEquals(2, names.size());
        assertEquals("星空", names.get("001.jpg"));
        assertEquals("Dawn", names.get("002.jpg"));
    }
}
