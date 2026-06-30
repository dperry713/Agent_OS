using Avalonia.Controls;
using Avalonia.Markup.Xaml;

namespace AgentOS.Frontend.Views
{
    public partial class Dashboard : UserControl
    {
        public Dashboard()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            AvaloniaXamlLoader.Load(this);
        }
    }
}
