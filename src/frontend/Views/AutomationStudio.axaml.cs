using Avalonia.Controls;
using Avalonia.Markup.Xaml;

namespace AgentOS.Frontend.Views
{
    public partial class AutomationStudio : UserControl
    {
        public AutomationStudio()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }
    }
}
