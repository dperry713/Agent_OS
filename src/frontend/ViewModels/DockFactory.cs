using System;
using System.Collections.Generic;
using Dock.Avalonia.Controls;
using Dock.Model.Controls;
using Dock.Model.Core;
using Dock.Model.Mvvm;
using Dock.Model.Mvvm.Controls;

namespace AgentOS.Desktop.ViewModels;

public class MainDockFactory : Factory
{
    public override IRootDock CreateLayout()
    {
        var document1 = new Document { Id = "Document1", Title = "Agent Log" };
        var document2 = new Document { Id = "Document2", Title = "System Info" };
        var tool1 = new Tool { Id = "Tool1", Title = "Toolbox" };
        var tool2 = new Tool { Id = "Tool2", Title = "Properties" };

        var mainLayout = new ProportionalDock
        {
            Id = "MainLayout",
            Orientation = Dock.Model.Core.Orientation.Horizontal,
            ActiveDockable = null,
            VisibleDockables = CreateList<IDockable>
            (
                new ToolDock
                {
                    Id = "LeftPane",
                    Proportion = 0.2,
                    ActiveDockable = tool1,
                    VisibleDockables = CreateList<IDockable>(tool1),
                    Alignment = Alignment.Left
                },
                new ProportionalDockSplitter(),
                new DocumentDock
                {
                    Id = "DocumentsPane",
                    Proportion = 0.6,
                    ActiveDockable = document1,
                    VisibleDockables = CreateList<IDockable>(document1, document2)
                },
                new ProportionalDockSplitter(),
                new ToolDock
                {
                    Id = "RightPane",
                    Proportion = 0.2,
                    ActiveDockable = tool2,
                    VisibleDockables = CreateList<IDockable>(tool2),
                    Alignment = Alignment.Right
                }
            )
        };

        var rootDock = CreateRootDock();

        rootDock.Id = "Root";
        rootDock.Title = "Root";
        rootDock.ActiveDockable = mainLayout;
        rootDock.DefaultDockable = mainLayout;
        rootDock.VisibleDockables = CreateList<IDockable>(mainLayout);

        return rootDock;
    }

    public override void InitLayout(IDockable layout)
    {
        ContextLocator = new Dictionary<string, Func<object?>>
        {
            ["Document1"] = () => new object(),
            ["Document2"] = () => new object(),
            ["Tool1"] = () => new object(),
            ["Tool2"] = () => new object()
        };

        HostWindowLocator = new Dictionary<string, Func<IHostWindow?>>
        {
            [nameof(IDockWindow)] = () => new HostWindow()
        };

        base.InitLayout(layout);
    }
}
