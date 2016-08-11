// habraproxy — это простейший локальный http-прокси-сервер, который показывает содержимое
// страниц Хабра. С одним исключением: после каждого слова из шести букв должен стоять
// значок «™». Примерно так:
//
// http://habrahabr.ru/company/yandex/blog/258673/
// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
// Сейчас на фоне уязвимости Logjam все в индустрии в очередной раз обсуждают проблемы и 
// особенности TLS. Я хочу воспользоваться этой возможностью, чтобы поговорить об одной из 
// них, а именно — о настройке ciphersiutes.
//
// http://127.0.0.1:8080/company/yandex/blog/258673/
// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
// Сейчас™ на фоне уязвимости Logjam™ все в индустрии в очередной раз обсуждают проблемы и 
// особенности TLS. Я хочу воспользоваться этой возможностью, чтобы поговорить об одной из 
// них, а именно™ — о настройке ciphersiutes. 
//
// Условия:
//   * ASP.NET MVC
//   * можно использовать любые общедоступные библиотеки, которые сочтёте нужным
//   * чем меньше кода, тем лучше
//   * все ссылки, ведущие на хабр на оригинальной странице, после обработки должны вести на прокси
//   * в случае, если не хватает каких-то данных, следует опираться на здравый смысл
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Text.RegularExpressions;
using System.Web.Mvc;
using AngleSharp.Dom;
using AngleSharp.Dom.Html;
using AngleSharp.Parser.Html;

namespace HabraproxyMVC.Controllers
{
    public class ProxyController : Controller
    {
        private static readonly Regex AddTradeMarkPattern;
        private static readonly Regex ReplaceUrlPattern;
        private const char TradeMarkChar = '™';
        private const string Source = "http://habrahabr.ru";

        static ProxyController()
        {
            const string tradeMarkPattern = @"(?<=\W|^)(?<word>[\w]{6})(?=\W|$)";
            const string urlPattern = @"((http|https)://)?habrahabr.ru";

            const RegexOptions options = RegexOptions.Compiled | RegexOptions.Multiline;

            AddTradeMarkPattern = new Regex(tradeMarkPattern, options);
            ReplaceUrlPattern = new Regex(urlPattern, options);
        }

        public ActionResult Index(string query = null)
        {
            if (Request.AcceptTypes.Contains(@"text/html"))
            {
                var request = (HttpWebRequest)WebRequest.Create(Source + '/' + query);
                var response = (HttpWebResponse)request.GetResponse();

                var parser = new HtmlParser();
                var dom = parser.Parse(response.GetResponseStream());

                var nodes = GetAllTextNodesFromDom(dom);
                foreach (var node in nodes)
                    node.TextContent = AddTradeMarkPattern.Replace(node.TextContent,
                        match => match.Groups["word"].Value + TradeMarkChar);

                var elements = GetAllLinksFromDom(dom);
                foreach (var element in elements)
                {
                    var url = element.Attributes["href"].Value;
                    element.Attributes["href"].Value = ReplaceUrlPattern.Replace(url, GetAppUrl());
                }

                return Content(dom.DocumentElement.OuterHtml, response.ContentType);
            }

            return Redirect(Source + '/' + query);
        }

        private string GetAppUrl()
        {
            return "http://" + Request.Url.Host + ":" + Request.Url.Port.ToString();
        }

        private static IHtmlCollection<IElement> GetAllLinksFromDom(IHtmlDocument dom)
        {
            return dom.DocumentElement.QuerySelectorAll("a[href]");
        }

        private static IEnumerable<INode> GetAllTextNodesFromDom(IHtmlDocument dom)
        {
            return dom.DocumentElement
                .QuerySelectorAll(":not(script), :not(style)")
                .SelectMany(
                    e => e.ChildNodes.Where(
                        n => n.NodeType == NodeType.Text));
        }
    }
}