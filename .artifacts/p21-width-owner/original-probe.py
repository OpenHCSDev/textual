"""Read our published scene, not a fresh layout."""
import json,os
from pathlib import Path
from textual.app import App
from toad.widgets.side_bar import SidebarResizeHandle
from toad.widgets.sidebar_viewport import SidebarHeader, SidebarViewport
from textual.widget import Widget
from toad.widgets.transcript_history import TranscriptPageView
from toad.widgets.history_anchor import HistoryWindow
from toad.widgets.throbber import Throbber
from toad.widgets.session_details import SessionDetails

def capture(out):
    state=json.loads((out/'live.json').read_text())
    if os.getpid()!=state['frontend']:raise RuntimeError('Not owned frontend')
    app=App.running_app()
    def snapshot():
        shown=app.screen._compositor.published_widgets
        rows=[]
        for node,(region,clip) in shown.items():
            if isinstance(node,SidebarResizeHandle):
                rows.append(dict(type=type(node).__name__,region=tuple(region),clip=tuple(clip),bar=node.parent.id))
        headers=[dict(type=type(node).__name__,region=tuple(region),clip=tuple(clip),
            ancestry=[dict(type=type(parent).__name__,region=tuple(parent.region),
                size=tuple(parent.size),virtual=tuple(parent.virtual_size),width=str(parent.styles.width))
                for parent in (node,*node.walk_ancestors()) if isinstance(parent,Widget)])
            for node,(region,clip) in shown.items() if isinstance(node,(SidebarHeader,SidebarViewport))]
        pages=[dict(page=id(page),type=type(page).__name__,width=page.line_width,
            admitted=len(page.fragments_in_range),stored=len(page.fragments),rows=page.line_count,
            region=tuple(shown[page][0]) if page in shown else None,
            clip=tuple(shown[page][1]) if page in shown else None)
            for page in app.screen.query(TranscriptPageView)]
        def painted(node):
            # Borrow the native row actually rendered; never call render_lines.
            row=node._styles_cache._cache.get(0)
            if row is None:return None
            def colour(value,foreground):
                return tuple(value.get_truecolor(app.ansi_theme,foreground=foreground)) if value else None
            return [dict(text=segment.text,
                foreground=colour(segment.style.color,True) if segment.style else None,
                background=colour(segment.style.bgcolor,False) if segment.style else None)
                for segment in row]
        result=dict(pid=os.getpid(),size=tuple(app.size),screen=type(app.screen).__name__,
            captured=repr(app.mouse_captured),selecting=app.screen._selecting,
            selected_session=repr(app.selected_session),source=type(app.workspace_sessions.source).__name__,
            source_view=repr(app.workspace_sessions.source.view),focused=repr(app.screen.focused),
            workers=[dict(name=w.name,group=w.group,state=str(w.state))for w in app.workers],
            controls=rows,headers=headers,pages=pages,theme=app.theme,
            animation_clock_time=vars(app.colours.clock).get('time'),
            activity_geometry=[dict(type=type(node).__name__,region=tuple(region),clip=tuple(clip),
                edge=edge.__name__ if (edge:=getattr(type(node),'ink_edge',None)) else None,
                painted=painted(node))
                for node,(region,clip) in shown.items() if isinstance(node,(Throbber,SessionDetails))],
            windows=[dict(kind=type(w).__name__,visible=w in shown,scroll=w.scroll_y,
                target=w.scroll_target_y,maximum=w.max_scroll_y,tail=w.follows_tail,
                pages=[id(page)for h in w.histories for page in h.pages])
                for w in app.screen.query(HistoryWindow)],
            modules={name:__import__(name,fromlist=['']).__file__ for name in
              ('toad.widgets.transcript_history','toad.widgets.side_bar','agent_comms','textual',
               'ui_theme.clock','ui_theme.effects')})
        (out/'scene.json').write_text(json.dumps(result,indent=2))
    # These are the published geometry and existing native row caches, not
    # a render request. Reading them needs no extra refresh or idle callback.
    snapshot()
