#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# SSHplus
# A remote connect utlity, sshmenu compatible clone, and application starter.
#
# (C) 2011 Anil Gulecha
# Based on sshlist, incorporating changes by Benjamin Heil's simplestarter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Instructions
#
# 1. Copy file sshplus.py (this file) to /usr/local/bin
# 2. Edit file .sshplus in your home directory to add menu entries, each
#    line in the format NAME|COMMAND|ARGS
# 3. Launch sshplus.py
# 4. Or better yet, add it to gnome startup programs list so it's run on login.

import gobject
import gtk
import appindicator
import os
import pynotify
import sys
import shlex
import re

_VERSION = "1.0"

_SETTINGS_FILE = os.getenv("HOME") + "/.sshplus"
_SSHMENU_FILE = os.getenv("HOME") + "/.sshmenu"
_TERMINAL_PROGRAM = os.environ.get('COLOR_TERM') or os.environ.get('TERM')

_ABOUT_TXT = """A simple application starter as appindicator.

To add items to the menu, edit the file <i>.sshplus</i> in your home directory. Each entry must be on a new line in this format:

<tt>NAME|COMMAND|ARGS</tt>

If the item is clicked in the menu, COMMAND with arguments ARGS will be executed. ARGS can be empty. To insert a separator, add a line which only contains "sep". Lines starting with "#" will be ignored. You can set an unclickable label with the prefix "label:". Items from sshmenu configuration will be automatically added (except nested items). To insert a nested menu, use the prefix "folder:menu name". Subsequent items will be inserted in this menu, until a line containing an empty folder name is found: "folder:". After that, subsequent items get inserted in the parent menu. That means that more than one level of nested menus can be created.

Example file:
<tt><small>
Show top|gnome-terminal|-x top
sep

# this is a comment
label:SSH connections
# create a folder named "Home"
folder:Home
SSH Ex|gnome-terminal|-x ssh user@1.2.3.4
# to mark the end of items inside "Home", specify and empty folder:
folder:
# this item appears in the main menu
SSH Ex|gnome-terminal|-x ssh user@1.2.3.4

label:RDP connections
RDP Ex|rdesktop|-T "RDP-Server" -r sound:local 1.2.3.4

</small></tt>
Copyright 2011 Anil Gulecha
Incorporating changes from simplestarter, Benjamin Heil, http://www.bheil.net

Released under GPL3, http://www.gnu.org/licenses/gpl-3.0.html"""



def menuitem_response(w, item):
    if item == '_about':
        show_help_dlg(_ABOUT_TXT)
    elif item == '_refresh':
        newmenu = build_menu()
        ind.set_menu(newmenu)
        pynotify.init("sshplus")
        pynotify.Notification("SSHplus refreshed", "Menu list was refreshed from %s" % _SETTINGS_FILE).show()
    elif item == '_config':
        show_config_window()
    elif item == '_quit':
        sys.exit(0)
    elif item == 'folder':
        pass
    else:
        print item
        os.spawnvp(os.P_NOWAIT, item['cmd'], [item['cmd']] + item['args'])
        os.wait3(os.WNOHANG)

def show_help_dlg(msg, error=False):
    if error:
        dlg_icon = gtk.MESSAGE_ERROR
    else:
        dlg_icon = gtk.MESSAGE_INFO
    md = gtk.MessageDialog(None, 0, dlg_icon, gtk.BUTTONS_OK)
    try:
        md.set_markup("<b>SSHplus %s</b>" % _VERSION)
        md.format_secondary_markup(msg)
        md.run()
    finally:
        md.destroy()

def show_config_window():
    apps = get_sshplusconfig()
    global config_window
    config_window = gtk.Window()
    config_window.set_title("Edit List")
    config_window.set_usize(350, 500)
    config_window.set_position(gtk.WIN_POS_CENTER)

    #List of connections
    vbox_list = gtk.VBox()
    listbox = gtk.List()
    global selected
    for app in apps:
        label = gtk.Label(app['name'])
        list_item = gtk.ListItem()
        list_item.add(label)
        list_item.connect("select", set_selected_item, app['name'])
        label.show()
        listbox.add(list_item)
    #Options
    vbox_options = gtk.VBox()
    #New Item Button
    hbox_new = gtk.HBox()
    button_new = gtk.Button("New")
    button_new.set_usize(50, 100)
    button_new.connect("clicked", edit_menu_item, True)
    hbox_new.add(button_new)
    vbox_options.add(hbox_new)
    #Edit Button
    hbox_edit = gtk.HBox()
    button_edit = gtk.Button("Edit")
    button_edit.set_usize(50, 100)
    button_edit.connect("clicked", edit_menu_item, False)
    hbox_edit.add(button_edit)
    vbox_options.add(hbox_edit)
    #Remove Button
    hbox_rm = gtk.HBox()
    button_rm = gtk.Button("Remove")
    button_rm.set_usize(50, 100)
    button_rm.connect("clicked", remove_menu_item)
    hbox_rm.add(button_rm)
    vbox_options.add(hbox_rm)
    #Add spacing
    empty_hbox = gtk.HBox()
    empty_hbox.set_usize(50, 485)
    vbox_options.add(empty_hbox)

    #layout list of apps
    scrollbox = gtk.ScrolledWindow()
    scrollbox.set_usize(250, 150)
    scrollbox.add_with_viewport(listbox)

    vbox_list.add(scrollbox)
    hbox = gtk.HBox()
    hbox.pack_start(vbox_list)
    hbox.pack_start(vbox_options)

    config_window.add(hbox)

    config_window.show_all()
    
def set_selected_item(self, name):
    global selected
    selected = name

def edit_menu_item(self, new):
    global edit_window 
    edit_window = gtk.Window()
    edit_window.set_position(gtk.WIN_POS_CENTER)
    vbox = gtk.VBox()
    label_name = gtk.Label("Name: ")
    text_name = gtk.Entry()
    label_cmd = gtk.Label("Command: ")
    text_cmd = gtk.Entry()
    label_args = gtk.Label("Arguments: ")
    text_args = gtk.Entry()
    hbox_name = gtk.HBox(True)
    hbox_cmd = gtk.HBox(True)
    hbox_args = gtk.HBox(True)
    vbox_name_label = gtk.VBox(True)
    vbox_name_label.add(label_name)
    vbox_name_label.set_properties()
    vbox_name_text = gtk.VBox(True)
    vbox_name_text.add(text_name)
    hbox_name.add(vbox_name_label)
    hbox_name.add(vbox_name_text)
    vbox_cmd_label = gtk.VBox(True)
    vbox_cmd_label.add(label_cmd)
    vbox_cmd_text = gtk.VBox(True)
    vbox_cmd_text.add(text_cmd)
    hbox_cmd.add(vbox_cmd_label)
    hbox_cmd.add(vbox_cmd_text)
    vbox_args_label = gtk.VBox(True)
    vbox_args_label.add(label_args)
    vbox_args_text = gtk.VBox(True)
    vbox_args_text.add(text_args)
    hbox_args.add(vbox_args_label)
    hbox_args.add(vbox_args_text)
    if new == True:
        edit_window.set_title("Add")
        if _TERMINAL_PROGRAM:
            text_cmd.set_text(_TERMINAL_PROGRAM)
        else:
            text_cmd.set_text("gnome-terminal")
        text_args.set_text("-x ssh user@host")
    else:
        global selected
        apps = get_sshplusconfig()
        for app in apps:
            if app['name'] == selected:
                text_name.set_text(app['name'])
                text_cmd.set_text(app['cmd'])
                text_args.set_text(" ".join(app['args']))
        edit_window.set_title("Edit")
        

    ok_button = gtk.Button("Save")
    ok_button.connect("clicked", save_item, text_name, text_cmd, text_args)
    vbox.add(hbox_name)
    vbox.add(hbox_cmd)
    vbox.add(hbox_args)
    vbox.add(ok_button)

    edit_window.add(vbox)
    edit_window.show_all()
    
def remove_menu_item(self):
    #Popup notifcation asking for confirmation
    window = gtk.Window()
    dialog = gtk.MessageDialog(window, gtk.DIALOG_MODAL,
                              gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO,
                              "Are you sure you want to delete entry?")
    dialog.set_title(":(")

    response = dialog.run()
    dialog.destroy()
    if response == gtk.RESPONSE_YES:
        hostlist = get_sshplusconfig()
        for item in hostlist:
            if item['name'] == selected:     
                index = hostlist.index(item)
                hostlist.pop(index)
                with open(_SETTINGS_FILE, 'wt') as hostfile:
                    for item in hostlist:
                        hostfile.write(str(item['name']) + '|' + str(item['cmd']) + '|' + str(" ".join(item['args'])) + '\n')
    position = config_window.get_position()
    config_window.destroy()
    config_window.move(position[0], position[1])
    show_config_window()   

def save_item(self, nametxtbox, cmdtxtbox, argstxtbox):
    name = nametxtbox.get_text()
    cmd = cmdtxtbox.get_text()
    args = argstxtbox.get_text().split()
    newitem = {'name': name, 'cmd': cmd, 'args': args}
    hostlist = get_sshplusconfig()
    found = False
    for item in hostlist:
        if item['name'] == name:
            found = True
            index = hostlist.index(item)
            hostlist.pop(index)
            hostlist.insert(index, newitem)
    if not found:
        hostlist.append(newitem)

    with open(_SETTINGS_FILE, 'wt') as hostfile:
        for item in hostlist:
            hostfile.write(str(item['name']) + '|' + str(item['cmd']) + '|' + str(" ".join(item['args'])) + '\n')

    hostfile.close()
    edit_window.destroy()
    config_window.destroy()
    show_config_window()
    

def add_separator(menu):
    separator = gtk.SeparatorMenuItem()
    separator.show()
    menu.append(separator)

def add_menu_item(menu, caption, item=None):
    menu_item = gtk.MenuItem(caption)
    if item:
        menu_item.connect("activate", menuitem_response, item)
    else:
        menu_item.set_sensitive(False)
    menu_item.show()
    menu.append(menu_item)
    return menu_item

def get_sshmenuconfig():
    if not os.path.exists(_SSHMENU_FILE):
        return []
    hostlist=open(_SSHMENU_FILE,"r").read()
    lines = hostlist.split("\n")
    lines.remove("items: ") #get rid of the first instance
    app_list = []
    
    smflag=0     # Flag to ignore submenu title items
    smtitle=""   # To hold the title while searching for parameters
    smparams=""  # To hold parameters values
    stackMenuIndex = []

    try:
        for line in lines:
            if re.search("title:",line):
                if smflag == 1:
                    smtitle=line.split(":", 1)[1]
                    continue
                smflag=1
                smtitle=line.split(":", 1)[1]

            elif re.search("sshparams:",line):
                smparams=line.split(":", 1)[1]
                smflag=2

            elif re.search("items:",line):
                app_list.append({
                    'name': 'FOLDER',
                    'cmd': "SSHmenu",
                    'args':"",
                })
                stackMenuIndex.append(len(app_list) - 1)

            elif re.search("type: menu",line):
                if smflag == 1:
                    app_list[stackMenuIndex.pop()]["cmd"] = smtitle
                    app_list.append({
                    'name': 'FOLDER',
                    'cmd': "",
                    'args':"",
                })
                    smflag = 0

            if smflag == 2:
                arglist = ("-x ssh " + smparams).split(" ")
                for a in arglist:
                    if a == "":
                        arglist.remove("")
                app_list.append({
                    'name': smtitle,
                    'cmd': 'gnome-terminal',
                    'args': arglist,
                 })
                smflag=0
        return app_list
    except:
        print "error in line:" + line
        return []

def get_sshplusconfig():
    if not os.path.exists(_SETTINGS_FILE):
        return []

    app_list = []
    f = open(_SETTINGS_FILE, "r")
    try:
        for line in f.readlines():
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            elif line == "sep":
                app_list.append('sep')
            elif line.startswith('label:'):
                app_list.append({
                    'name': 'LABEL',
                    'cmd': line[6:], 
                    'args': ''
                })
            elif line.startswith('folder:'):
                app_list.append({
                    'name': 'FOLDER',
                    'cmd': line[7:], 
                    'args': ''
                })
            else:
                try:
                    name, cmd, args = line.split('|', 2)
                    app_list.append({
                        'name': name,
                        'cmd': cmd,
                        'args': [n.replace("\n", "") for n in shlex.split(args)],
                    })
                except ValueError:
                    print "The following line has errors and will be ignored:\n%s" % line
    finally:
        f.close()
    return app_list

def build_menu():
    if not os.path.exists(_SETTINGS_FILE) and not os.path.exists(_SSHMENU_FILE) :
        alert = gtk.MessageDialog(parent=None, flags=0, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK)
        alert.set_markup("<b>ERROR: No .sshmenu or .sshplus file found in home directory</b>\n\n.sshplus file will be created, please use menu once you hit OK to add menu options.")
        alert.run()
        open(_SETTINGS_FILE, "a").close()
        show_config_window()
        alert.do_close(alert)

    app_list = get_sshplusconfig()

    #Add sshmenu config items if any
    app_list2 = get_sshmenuconfig()
    if app_list2 != []:
        app_list = app_list + ["sep",{'name': 'LABEL','cmd': "SSHmenu",'args': ''}] + app_list2

    menu = gtk.Menu()
    menus = [menu]

    for app in app_list:
        if app == "sep":
            add_separator(menus[-1])
        elif app['name'] == "FOLDER" and not app['cmd']:
            if len(menus) > 1:
                menus.pop()
        elif app['name'] == "FOLDER":
            menu_item = add_menu_item(menus[-1], app['cmd'], 'folder')
            menus.append(gtk.Menu())
            menu_item.set_submenu(menus[-1])
        elif app['name'] == "LABEL":
            add_menu_item(menus[-1], app['cmd'], None)
        else:
            add_menu_item(menus[-1], app['name'], app)

    add_separator(menu)
    add_menu_item(menu, 'Refresh', '_refresh')
    add_menu_item(menu, 'Edit List', '_config')
    add_menu_item(menu, 'About', '_about')
    add_separator(menu)
    add_menu_item(menu, 'Quit', '_quit')
    return menu

if __name__ == "__main__":
    ind = appindicator.Indicator("sshplu", "gnome-netstatus-tx",
                                 appindicator.CATEGORY_APPLICATION_STATUS)
    ind.set_label("Launch")
    ind.set_status(appindicator.STATUS_ACTIVE)

    appmenu = build_menu()
    ind.set_menu(appmenu)
    gtk.main()
