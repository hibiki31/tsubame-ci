/**
 * Vuetify3プラグイン設定
 */
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import '@mdi/font/css/materialdesignicons.css'

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: 'tsubameLight',
    themes: {
      tsubameLight: {
        dark: false,
        colors: {
          background: '#F4F6F3',
          surface: '#FFFFFF',
          'surface-bright': '#FFFFFF',
          'surface-light': '#F8FAF8',
          'surface-variant': '#E8EEEB',
          'on-surface-variant': '#5F6B68',
          primary: '#174A48',
          'primary-soft': '#E3F0EC',
          secondary: '#5D6B68',
          accent: '#C9682B',
          error: '#B4473D',
          info: '#2F7086',
          success: '#287557',
          warning: '#A96317',
        },
        variables: {
          'border-color': '#173D3B',
          'border-opacity': 0.12,
          'high-emphasis-opacity': 0.9,
          'medium-emphasis-opacity': 0.68,
          'focus-opacity': 0.08,
          'hover-opacity': 0.05,
          'selected-opacity': 0.09,
          'activated-opacity': 0.11,
        },
      },
    },
  },
  defaults: {
    VBtn: {
      rounded: 'lg',
      class: 'text-none',
    },
    VCard: {
      elevation: 0,
      rounded: 'xl',
      variant: 'flat',
    },
    VDialog: {
      scrollable: true,
    },
    VTextField: {
      color: 'primary',
      density: 'comfortable',
      variant: 'outlined',
    },
    VTextarea: {
      color: 'primary',
      density: 'comfortable',
      variant: 'outlined',
    },
    VSelect: {
      color: 'primary',
      density: 'comfortable',
      variant: 'outlined',
    },
  },
})

export default vuetify
