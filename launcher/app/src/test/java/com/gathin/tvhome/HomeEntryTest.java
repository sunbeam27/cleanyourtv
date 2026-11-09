package com.gathin.tvhome;

import org.junit.Test;
import static org.junit.Assert.*;

public class HomeEntryTest {
    @Test public void ordinaryAppTrialCanExit() {
        HomeEntry entry = new HomeEntry();
        entry.launch(false);
        assertTrue(entry.canExit(true));
    }

    @Test public void realHomeDoesNotExit() {
        HomeEntry entry = new HomeEntry();
        entry.launch(true);
        assertFalse(entry.canExit(true));
    }

    @Test public void repeatedSingleTaskLaunchesUseLatestEntry() {
        HomeEntry entry = new HomeEntry();
        entry.launch(false);
        entry.launch(true);
        assertFalse(entry.canExit(true));
        entry.launch(false);
        assertTrue(entry.canExit(true));
    }

    @Test public void recreationPreservesHomeEntry() {
        HomeEntry before = new HomeEntry();
        before.launch(true);
        HomeEntry after = new HomeEntry();
        after.launch(before.isHome());
        assertFalse(after.canExit(true));
    }

    @Test public void recreationPreservesAppEntry() {
        HomeEntry before = new HomeEntry();
        before.launch(false);
        HomeEntry after = new HomeEntry();
        after.launch(before.isHome());
        assertTrue(after.canExit(true));
    }

    @Test public void standardLauncherKeepsExistingBackBehaviour() {
        HomeEntry entry = new HomeEntry();
        entry.launch(false);
        assertFalse(entry.canExit(false));
        entry.launch(true);
        assertFalse(entry.canExit(false));
    }
}
