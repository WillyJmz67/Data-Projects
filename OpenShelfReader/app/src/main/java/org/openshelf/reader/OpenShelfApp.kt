package org.openshelf.reader

import android.app.Application
import org.openshelf.reader.di.AppContainer

class OpenShelfApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
