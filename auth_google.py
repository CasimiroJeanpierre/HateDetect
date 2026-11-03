"""Google Identity Services -> Supabase Auth, using ONLY a publishable key.

The Google ID token is validated by Supabase Auth. Never store it in a URL,
render it on screen, write it to logs, or cache the authenticated Supabase
client globally. All authenticated clients are kept per Streamlit session.
"""

from __future__ import annotations

import streamlit as st
from supabase import create_client


GOOGLE_BUTTON_HTML = '<div class="hatedetect-google-signin" aria-label="Acceso con Google"></div>'
GOOGLE_BUTTON_JS = r"""
export default function(component) {
  const { parentElement, setTriggerValue, data } = component;
  const target = parentElement.querySelector('.hatedetect-google-signin');
  const source = 'https://accounts.google.com/gsi/client';
  let active = true;
  function render() {
    if (!active || !window.google?.accounts?.id) return;
    target.replaceChildren();
    window.google.accounts.id.initialize({
      client_id: data.client_id,
      callback: (response) => {
        if (active && response?.credential) {
          setTriggerValue('credential', response.credential);
        }
      },
      auto_select: false,
      ux_mode: 'popup',
      use_fedcm_for_prompt: true
    });
    window.google.accounts.id.renderButton(target, {
      theme: 'outline', size: 'large', shape: 'pill', text: 'signin_with'
    });
  }
  if (window.google?.accounts?.id) {
    render();
  } else {
    let loader = document.querySelector('script[data-hatedetect-google-sdk]');
    if (!loader) {
      loader = document.createElement('script');
      loader.src = source;
      loader.async = true;
      loader.defer = true;
      loader.dataset.hatedetectGoogleSdk = '1';
      document.head.appendChild(loader);
    }
    loader.addEventListener('load', render, { once: true });
  }
  return () => { active = false; };
}
"""


def _google_button():
    return st.components.v2.component(
        "hatedetect_google_identity",
        html=GOOGLE_BUTTON_HTML,
        js=GOOGLE_BUTTON_JS,
        isolate_styles=False,
    )


def configuration():
    """Return only public identifiers. Google OAuth secret stays in Supabase."""
    try:
        google_id = str(st.secrets["google"]["client_id"]).strip()
        url = str(st.secrets["supabase"]["url"]).strip()
        key = str(st.secrets["supabase"]["publishable_key"]).strip()
        if not google_id.endswith('.apps.googleusercontent.com'):
            raise ValueError('Google Client ID inválido')
        if not url.startswith('https://') or not key.startswith('sb_publishable_'):
            raise ValueError('Configuración de Supabase inválida')
        return google_id, url, key
    except Exception:
        # Streamlit puede lanzar StreamlitSecretNotFoundError al faltar secrets.toml.
        return None


def active_user():
    """Session-scoped Supabase client and verified Auth user ID, or (None,None)."""
    client = st.session_state.get('hatedetect_auth_client')
    uid = st.session_state.get('hatedetect_auth_uid')
    if client is not None and uid:
        return client, uid
    return None, None


def logout():
    client, _ = active_user()
    st.session_state.pop('hatedetect_auth_client', None)
    st.session_state.pop('hatedetect_auth_uid', None)
    st.session_state.pop('hatedetect_auth_email', None)
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    st.rerun()


def render_login():
    """Show a Google button and accept only a token verified by Supabase."""
    client, uid = active_user()
    if uid:
        st.sidebar.caption('Sesión: ' + str(st.session_state.get('hatedetect_auth_email', 'Google')))
        if st.sidebar.button('Cerrar sesión', key='logout_cloud'):
            logout()
        return client, uid

    conf = configuration()
    if conf is None:
        st.sidebar.info('Acceso opcional: configura Google y Supabase para activar Historial persistente.')
        return None, None

    google_id, url, key = conf
    st.sidebar.caption('Inicia sesión con Google para guardar Historial permanente.')
    token_event = _google_button()(data={'client_id': google_id},
                                   key='google_login_widget',
                                   on_credential_change=lambda: None)
    id_token = getattr(token_event, 'credential', None)
    if not id_token:
        return None, None
    try:
        # Per-session client: NEVER place auth clients in @st.cache_resource.
        client = create_client(url, key)
        result = client.auth.sign_in_with_id_token({
            'provider': 'google', 'token': id_token
        })
        if not result.session or not result.user or not result.user.id:
            raise ValueError('La identidad no fue aceptada por Supabase')
        st.session_state['hatedetect_auth_client'] = client
        st.session_state['hatedetect_auth_uid'] = str(result.user.id)
        st.session_state['hatedetect_auth_email'] = str(result.user.email or 'Cuenta Google')
        st.rerun()
    except Exception:
        # Never print OAuth tokens or auth provider exceptions containing them.
        st.sidebar.error('No se pudo validar la sesión. Verifica Google OAuth y vuelve a intentar.')
        return None, None


def save_history(client, uid, cleaned, category, milliseconds):
    """RLS enforces Auth UID; no user_id is accepted from the browser."""
    if client is None or not uid:
        raise PermissionError('Se necesita iniciar sesión')
    if category not in {'Odio', 'Ofensivo', 'Neutro'} or not 1 <= len(cleaned) <= 2000:
        raise ValueError('Datos inválidos')
    payload = {
        'comment_text': cleaned,
        'category': category,
        'model_name': 'TF-IDF + LogisticRegression',
        'inference_ms': max(0.0, round(float(milliseconds), 3)),
    }
    return client.table('hatedetect_history').insert(payload).execute()


def list_history(client, uid):
    if client is None or not uid:
        raise PermissionError('Se necesita iniciar sesión')
    return (client.table('hatedetect_history')
            .select('id,created_at,comment_text,category,model_name,inference_ms')
            .eq('user_id', uid)
            .order('created_at', desc=True)
            .limit(100).execute().data or [])


def delete_history(client, uid, record_id):
    if client is None or not uid:
        raise PermissionError('Se necesita iniciar sesión')
    return (client.table('hatedetect_history').delete()
            .eq('user_id', uid).eq('id', record_id).execute())
