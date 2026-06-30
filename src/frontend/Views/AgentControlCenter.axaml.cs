using Avalonia.Controls;
using Avalonia.Markup.Xaml;

namespace AgentOS.Frontend.Views
{
    public partial class AgentControlCenter : UserControl
    {
        public AgentControlCenter()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }
    }
}
